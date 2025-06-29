"""
Optimized CGM Analyzer with async I/O and enhanced caching
"""

import asyncio
import os
from pathlib import Path
from typing import List, Optional

import aiofiles
from loguru import logger

from .analyzer import CGMAnalyzer
from ..models import FileAnalysis


class OptimizedCGMAnalyzer(CGMAnalyzer):
    """
    Enhanced CGM analyzer with async file I/O and performance optimizations
    """

    def __init__(self):
        super().__init__()
        self.max_file_size = 2 * 1024 * 1024  # 2MB limit (increased from 1MB)
        self.max_concurrent_files = 10  # Limit concurrent file operations

    async def _analyze_single_file_async(
        self, file_path: str, relative_path: str
    ) -> Optional[FileAnalysis]:
        """Async version of single file analysis"""
        try:
            # Check file size first
            if not os.path.exists(file_path):
                return None
                
            file_size = os.path.getsize(file_path)
            if file_size > self.max_file_size:
                logger.warning(f"Skipping large file {relative_path} ({file_size} bytes)")
                return None

            # Read file asynchronously
            async with aiofiles.open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = await f.read()

            # Extract structure
            structure = self._extract_file_structure(content, relative_path)

            # Extract imports/dependencies
            dependencies = self._extract_dependencies(content, relative_path)

            return FileAnalysis(
                file_path=relative_path,
                content=content,
                structure=structure,
                dependencies=dependencies,
                metadata={
                    "size": len(content),
                    "lines": content.count("\n") + 1,
                    "language": self._detect_language(relative_path),
                    "file_size_bytes": file_size,
                },
            )

        except Exception as e:
            logger.warning(f"Failed to analyze file {file_path}: {e}")
            return None

    async def _analyze_files_concurrent(
        self, repo_path: str, entities: List, max_files: int = 10
    ) -> List[FileAnalysis]:
        """Analyze files concurrently with semaphore to limit concurrent operations"""
        file_analyses = []
        processed_files = set()
        
        # Create semaphore to limit concurrent file operations
        semaphore = asyncio.Semaphore(self.max_concurrent_files)
        
        async def analyze_file_with_semaphore(entity):
            async with semaphore:
                if entity.file_path in processed_files:
                    return None
                    
                file_path = os.path.join(repo_path, entity.file_path)
                if os.path.exists(file_path):
                    analysis = await self._analyze_single_file_async(file_path, entity.file_path)
                    if analysis:
                        processed_files.add(entity.file_path)
                        return analysis
                return None

        # Create tasks for concurrent execution
        tasks = []
        for entity in entities:
            if len(tasks) >= max_files:
                break
            tasks.append(analyze_file_with_semaphore(entity))

        # Execute tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out None results and exceptions
        for result in results:
            if isinstance(result, FileAnalysis):
                file_analyses.append(result)
            elif isinstance(result, Exception):
                logger.warning(f"File analysis failed: {result}")

        return file_analyses

    async def _build_code_graph_async(self, repo_path: str):
        """Async version of code graph building with concurrent file processing"""
        import networkx as nx
        from ..models import CodeGraph
        
        graph = nx.DiGraph()
        files = []
        entities = []

        # Collect all files first
        file_tasks = []
        semaphore = asyncio.Semaphore(self.max_concurrent_files)
        
        async def process_file_with_semaphore(file_path, relative_path):
            async with semaphore:
                if self._should_analyze_file(file_path):
                    file_entities = await self._analyze_file_structure_async(
                        file_path, relative_path
                    )
                    return relative_path, file_entities
                return None, []

        # Walk through directory and create tasks
        for root, dirs, file_names in os.walk(repo_path):
            # Skip common non-source directories
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".")
                and d not in {"node_modules", "__pycache__", "build", "dist", "target"}
            ]

            for file_name in file_names:
                file_path = os.path.join(root, file_name)
                relative_path = os.path.relpath(file_path, repo_path)
                file_tasks.append(process_file_with_semaphore(file_path, relative_path))

        # Process files concurrently
        results = await asyncio.gather(*file_tasks, return_exceptions=True)
        
        # Process results
        for result in results:
            if isinstance(result, tuple) and result[0] is not None:
                relative_path, file_entities = result
                files.append(relative_path)
                entities.extend(file_entities)
                
                # Add to graph
                self._add_file_to_graph(graph, relative_path, file_entities)
            elif isinstance(result, Exception):
                logger.warning(f"File processing failed: {result}")

        return CodeGraph(
            files=files, entities=entities, graph_data=self._serialize_graph(graph)
        )

    async def _analyze_file_structure_async(
        self, file_path: str, relative_path: str
    ) -> List:
        """Async version of file structure analysis"""
        entities = []

        try:
            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size > self.max_file_size:
                return entities

            async with aiofiles.open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = await f.read()

            if file_path.endswith(".py"):
                entities = self._analyze_python_file(content, relative_path)
            else:
                entities = self._analyze_generic_file(content, relative_path)

        except Exception as e:
            logger.warning(f"Failed to analyze file structure {file_path}: {e}")

        return entities

    def _should_analyze_file(self, file_path: str) -> bool:
        """Enhanced file filtering with size check"""
        ext = Path(file_path).suffix.lower()
        try:
            file_size = os.path.getsize(file_path)
            return (
                ext in self.supported_extensions
                and file_size < self.max_file_size
                and file_size > 0  # Skip empty files
            )
        except OSError:
            return False

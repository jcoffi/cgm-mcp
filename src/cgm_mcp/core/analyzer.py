"""
CGM Core Analyzer - Model-agnostic code analysis engine

This module provides the core CGM functionality without depending on any specific LLM.
It extracts code structure, builds graphs, and provides context for external models.
"""

import ast
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx
from loguru import logger

from ..models import (
    CodeAnalysisRequest,
    CodeAnalysisResponse,
    CodeEntity,
    CodeGraph,
    CodeRelation,
    FileAnalysis,
)


class CGMAnalyzer:
    """
    Model-agnostic CGM analyzer that provides code structure analysis,
    graph building, and context extraction without requiring LLM calls.
    """

    def __init__(self):
        self.supported_extensions = {
            # Python
            ".py", ".pyx", ".pyi",
            # JavaScript/TypeScript
            ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
            # Java/Kotlin/Scala
            ".java", ".kt", ".scala",
            # C/C++
            ".c", ".cpp", ".cc", ".cxx", ".h", ".hpp", ".hxx",
            # Go
            ".go",
            # Rust
            ".rs",
            # PHP
            ".php", ".php3", ".php4", ".php5", ".phtml",
            # Ruby
            ".rb", ".rbw",
            # C#
            ".cs",
            # Swift
            ".swift",
            # Objective-C
            ".m", ".mm",
            # Dart
            ".dart",
            # Lua
            ".lua",
            # Shell
            ".sh", ".bash", ".zsh", ".fish",
            # SQL
            ".sql",
            # R
            ".r", ".R",
            # MATLAB
            ".m",
            # Perl
            ".pl", ".pm",
            # Haskell
            ".hs",
            # Erlang/Elixir
            ".erl", ".ex", ".exs",
            # Clojure
            ".clj", ".cljs", ".cljc",
            # F#
            ".fs", ".fsx",
            # Visual Basic
            ".vb",
            # PowerShell
            ".ps1", ".psm1",
        }

    async def analyze_repository(
        self, request: CodeAnalysisRequest
    ) -> CodeAnalysisResponse:
        """
        Analyze repository and return structured information for external models
        """
        try:
            logger.info(f"Analyzing repository: {request.repository_path}")

            # Build code graph
            code_graph = await self._build_code_graph(request.repository_path)

            # Extract entities based on query
            relevant_entities = self._extract_relevant_entities(
                code_graph, request.query, request.focus_files
            )

            # Get file analysis
            file_analyses = await self._analyze_files(
                request.repository_path, relevant_entities, request.max_files
            )

            # Extract code relations
            relations = self._extract_relations(code_graph, relevant_entities)

            # Generate context summary
            context_summary = self._generate_context_summary(
                code_graph, relevant_entities, file_analyses
            )

            return CodeAnalysisResponse(
                repository_path=request.repository_path,
                code_graph=code_graph,
                relevant_entities=relevant_entities,
                file_analyses=file_analyses,
                relations=relations,
                context_summary=context_summary,
                analysis_metadata={
                    "total_files": len(code_graph.files),
                    "total_entities": len(relevant_entities),
                    "analysis_scope": request.analysis_scope,
                },
            )

        except Exception as e:
            logger.error(f"Error analyzing repository: {e}")
            raise

    async def _build_code_graph(self, repo_path: str) -> CodeGraph:
        """Build comprehensive code graph from repository"""
        graph = nx.DiGraph()
        files = []
        entities = []

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

                if self._should_analyze_file(file_path):
                    file_entities = await self._analyze_file_structure(
                        file_path, relative_path
                    )
                    files.append(relative_path)
                    entities.extend(file_entities)

                    # Add to graph
                    self._add_file_to_graph(graph, relative_path, file_entities)

        return CodeGraph(
            files=files, entities=entities, graph_data=self._serialize_graph(graph)
        )

    def _should_analyze_file(self, file_path: str) -> bool:
        """Check if file should be analyzed"""
        ext = Path(file_path).suffix.lower()
        return (
            ext in self.supported_extensions
            and os.path.getsize(file_path) < 1024 * 1024
        )  # 1MB limit

    async def _analyze_file_structure(
        self, file_path: str, relative_path: str
    ) -> List[CodeEntity]:
        """Analyze file structure and extract entities"""
        entities = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            if file_path.endswith(".py"):
                entities = self._analyze_python_file(content, relative_path)
            elif file_path.endswith((".php", ".php3", ".php4", ".php5", ".phtml")):
                entities = self._analyze_php_file(content, relative_path)
            elif file_path.endswith((".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")):
                entities = self._analyze_javascript_file(content, relative_path)
            elif file_path.endswith((".java", ".kt", ".scala")):
                entities = self._analyze_java_like_file(content, relative_path)
            elif file_path.endswith((".c", ".cpp", ".cc", ".cxx", ".h", ".hpp", ".hxx")):
                entities = self._analyze_c_like_file(content, relative_path)
            elif file_path.endswith(".go"):
                entities = self._analyze_go_file(content, relative_path)
            elif file_path.endswith(".rs"):
                entities = self._analyze_rust_file(content, relative_path)
            elif file_path.endswith((".rb", ".rbw")):
                entities = self._analyze_ruby_file(content, relative_path)
            elif file_path.endswith(".cs"):
                entities = self._analyze_csharp_file(content, relative_path)
            else:
                entities = self._analyze_generic_file(content, relative_path)

        except Exception as e:
            logger.warning(f"Failed to analyze file {file_path}: {e}")

        return entities

    def _analyze_python_file(self, content: str, file_path: str) -> List[CodeEntity]:
        """Analyze Python file using AST"""
        entities = []

        try:
            tree = ast.parse(content)

            # Add file entity
            entities.append(
                CodeEntity(
                    id=f"file:{file_path}",
                    type="file",
                    name=os.path.basename(file_path),
                    file_path=file_path,
                    content_preview=content[:500],
                    metadata={"language": "python", "size": len(content)},
                )
            )

            # Extract classes and functions
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    entities.append(self._create_class_entity(node, file_path))
                elif isinstance(node, ast.FunctionDef):
                    entities.append(self._create_function_entity(node, file_path))

        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
        except Exception as e:
            logger.warning(f"Error analyzing Python file {file_path}: {e}")

        return entities

    def _analyze_php_file(self, content: str, file_path: str) -> List[CodeEntity]:
        """Analyze PHP file using regex patterns"""
        entities = []

        try:
            # Add file entity
            entities.append(CodeEntity(
                id=f"file:{file_path}",
                type="file",
                name=os.path.basename(file_path),
                file_path=file_path,
                content_preview=content[:500],
                metadata={"language": "php", "size": len(content)}
            ))

            # Extract PHP classes
            class_pattern = r'(?:abstract\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w,\s]+))?\s*\{'
            for match in re.finditer(class_pattern, content, re.MULTILINE):
                class_name = match.group(1)
                extends = match.group(2)
                implements = match.group(3)
                line_num = content[:match.start()].count('\n') + 1

                # Extract methods for this class
                class_start = match.start()
                brace_count = 0
                class_end = class_start
                for i, char in enumerate(content[class_start:], class_start):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            class_end = i
                            break

                class_content = content[class_start:class_end]
                methods = self._extract_php_methods(class_content)

                entities.append(CodeEntity(
                    id=f"class:{file_path}:{class_name}",
                    type="class",
                    name=class_name,
                    file_path=file_path,
                    content_preview=class_content[:200],
                    metadata={
                        "extends": extends,
                        "implements": implements.split(',') if implements else [],
                        "methods": methods,
                        "line_start": line_num,
                        "visibility": "public"
                    }
                ))

            # Extract PHP functions (not in classes)
            function_pattern = r'(?:public\s+|private\s+|protected\s+)?function\s+(\w+)\s*\([^)]*\)'
            for match in re.finditer(function_pattern, content, re.MULTILINE):
                function_name = match.group(1)
                line_num = content[:match.start()].count('\n') + 1

                # Skip if this function is inside a class
                before_function = content[:match.start()]
                class_count = before_function.count('class ')
                class_end_count = before_function.count('}')

                if class_count <= class_end_count:  # Function is not inside a class
                    entities.append(CodeEntity(
                        id=f"function:{file_path}:{function_name}",
                        type="function",
                        name=function_name,
                        file_path=file_path,
                        content_preview="",
                        metadata={
                            "line_start": line_num,
                            "visibility": self._extract_php_visibility(match.group(0))
                        }
                    ))

            # Extract PHP interfaces
            interface_pattern = r'interface\s+(\w+)(?:\s+extends\s+([\w,\s]+))?\s*\{'
            for match in re.finditer(interface_pattern, content, re.MULTILINE):
                interface_name = match.group(1)
                extends = match.group(2)
                line_num = content[:match.start()].count('\n') + 1

                entities.append(CodeEntity(
                    id=f"interface:{file_path}:{interface_name}",
                    type="interface",
                    name=interface_name,
                    file_path=file_path,
                    content_preview="",
                    metadata={
                        "extends": extends.split(',') if extends else [],
                        "line_start": line_num
                    }
                ))

            # Extract PHP traits
            trait_pattern = r'trait\s+(\w+)\s*\{'
            for match in re.finditer(trait_pattern, content, re.MULTILINE):
                trait_name = match.group(1)
                line_num = content[:match.start()].count('\n') + 1

                entities.append(CodeEntity(
                    id=f"trait:{file_path}:{trait_name}",
                    type="trait",
                    name=trait_name,
                    file_path=file_path,
                    content_preview="",
                    metadata={"line_start": line_num}
                ))

        except Exception as e:
            logger.warning(f"Error analyzing PHP file {file_path}: {e}")

        return entities

    def _extract_php_methods(self, class_content: str) -> List[str]:
        """Extract method names from PHP class content"""
        methods = []
        method_pattern = r'(?:public\s+|private\s+|protected\s+|static\s+)*function\s+(\w+)\s*\('
        for match in re.finditer(method_pattern, class_content, re.MULTILINE):
            methods.append(match.group(1))
        return methods

    def _extract_php_visibility(self, function_declaration: str) -> str:
        """Extract visibility from PHP function declaration"""
        if 'private' in function_declaration:
            return 'private'
        elif 'protected' in function_declaration:
            return 'protected'
        else:
            return 'public'

    def _analyze_javascript_file(self, content: str, file_path: str) -> List[CodeEntity]:
        """Analyze JavaScript/TypeScript file using regex patterns"""
        entities = []

        try:
            # Add file entity
            entities.append(CodeEntity(
                id=f"file:{file_path}",
                type="file",
                name=os.path.basename(file_path),
                file_path=file_path,
                content_preview=content[:500],
                metadata={"language": "javascript", "size": len(content)}
            ))

            # Extract classes
            class_patterns = [
                r'class\s+(\w+)(?:\s+extends\s+(\w+))?\s*\{',  # ES6 classes
                r'(\w+)\s*=\s*class(?:\s+extends\s+(\w+))?\s*\{',  # Class expressions
            ]

            for pattern in class_patterns:
                for match in re.finditer(pattern, content, re.MULTILINE):
                    class_name = match.group(1)
                    extends = match.group(2) if len(match.groups()) > 1 else None
                    line_num = content[:match.start()].count('\n') + 1

                    entities.append(CodeEntity(
                        id=f"class:{file_path}:{class_name}",
                        type="class",
                        name=class_name,
                        file_path=file_path,
                        content_preview="",
                        metadata={
                            "extends": extends,
                            "line_start": line_num
                        }
                    ))

            # Extract functions
            function_patterns = [
                r'function\s+(\w+)\s*\(',  # Function declarations
                r'(\w+)\s*:\s*function\s*\(',  # Object method
                r'(\w+)\s*=\s*function\s*\(',  # Function expressions
                r'(\w+)\s*=\s*\([^)]*\)\s*=>', # Arrow functions
                r'async\s+function\s+(\w+)\s*\(',  # Async functions
            ]

            for pattern in function_patterns:
                for match in re.finditer(pattern, content, re.MULTILINE):
                    function_name = match.group(1)
                    line_num = content[:match.start()].count('\n') + 1

                    entities.append(CodeEntity(
                        id=f"function:{file_path}:{function_name}",
                        type="function",
                        name=function_name,
                        file_path=file_path,
                        content_preview="",
                        metadata={"line_start": line_num}
                    ))

            # Extract TypeScript interfaces (if .ts file)
            if file_path.endswith(('.ts', '.tsx')):
                interface_pattern = r'interface\s+(\w+)(?:\s+extends\s+([\w,\s]+))?\s*\{'
                for match in re.finditer(interface_pattern, content, re.MULTILINE):
                    interface_name = match.group(1)
                    extends = match.group(2)
                    line_num = content[:match.start()].count('\n') + 1

                    entities.append(CodeEntity(
                        id=f"interface:{file_path}:{interface_name}",
                        type="interface",
                        name=interface_name,
                        file_path=file_path,
                        content_preview="",
                        metadata={
                            "extends": extends.split(',') if extends else [],
                            "line_start": line_num
                        }
                    ))

        except Exception as e:
            logger.warning(f"Error analyzing JavaScript file {file_path}: {e}")

        return entities

    def _analyze_java_like_file(self, content: str, file_path: str) -> List[CodeEntity]:
        """Analyze Java/Kotlin/Scala files"""
        entities = []

        try:
            # Add file entity
            language = "java"
            if file_path.endswith(".kt"):
                language = "kotlin"
            elif file_path.endswith(".scala"):
                language = "scala"

            entities.append(CodeEntity(
                id=f"file:{file_path}",
                type="file",
                name=os.path.basename(file_path),
                file_path=file_path,
                content_preview=content[:500],
                metadata={"language": language, "size": len(content)}
            ))

            # Extract classes
            class_patterns = [
                r'(?:public\s+|private\s+|protected\s+)?(?:abstract\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w,\s]+))?\s*\{',
                r'(?:public\s+|private\s+|protected\s+)?interface\s+(\w+)(?:\s+extends\s+([\w,\s]+))?\s*\{',
                r'(?:public\s+|private\s+|protected\s+)?enum\s+(\w+)\s*\{',
            ]

            for pattern in class_patterns:
                for match in re.finditer(pattern, content, re.MULTILINE):
                    class_name = match.group(1)
                    line_num = content[:match.start()].count('\n') + 1

                    # Determine type
                    declaration = match.group(0)
                    if 'interface' in declaration:
                        entity_type = 'interface'
                    elif 'enum' in declaration:
                        entity_type = 'enum'
                    else:
                        entity_type = 'class'

                    entities.append(CodeEntity(
                        id=f"{entity_type}:{file_path}:{class_name}",
                        type=entity_type,
                        name=class_name,
                        file_path=file_path,
                        content_preview="",
                        metadata={"line_start": line_num}
                    ))

            # Extract methods
            method_pattern = r'(?:public\s+|private\s+|protected\s+|static\s+)*(?:\w+\s+)*(\w+)\s*\([^)]*\)\s*\{'
            for match in re.finditer(method_pattern, content, re.MULTILINE):
                method_name = match.group(1)
                line_num = content[:match.start()].count('\n') + 1

                # Skip constructors and common keywords
                if method_name not in ['if', 'for', 'while', 'switch', 'try', 'catch']:
                    entities.append(CodeEntity(
                        id=f"method:{file_path}:{method_name}",
                        type="method",
                        name=method_name,
                        file_path=file_path,
                        content_preview="",
                        metadata={"line_start": line_num}
                    ))

        except Exception as e:
            logger.warning(f"Error analyzing Java-like file {file_path}: {e}")

        return entities

    def _analyze_c_like_file(self, content: str, file_path: str) -> List[CodeEntity]:
        """Analyze C/C++ files"""
        entities = []

        try:
            # Add file entity
            language = "c" if file_path.endswith(('.c', '.h')) else "cpp"
            entities.append(CodeEntity(
                id=f"file:{file_path}",
                type="file",
                name=os.path.basename(file_path),
                file_path=file_path,
                content_preview=content[:500],
                metadata={"language": language, "size": len(content)}
            ))

            # Extract functions
            function_pattern = r'(?:static\s+|inline\s+|extern\s+)*(?:\w+\s+\*?\s*)+(\w+)\s*\([^)]*\)\s*\{'
            for match in re.finditer(function_pattern, content, re.MULTILINE):
                function_name = match.group(1)
                line_num = content[:match.start()].count('\n') + 1

                # Skip common keywords
                if function_name not in ['if', 'for', 'while', 'switch', 'return']:
                    entities.append(CodeEntity(
                        id=f"function:{file_path}:{function_name}",
                        type="function",
                        name=function_name,
                        file_path=file_path,
                        content_preview="",
                        metadata={"line_start": line_num}
                    ))

            # Extract structs/classes (C++)
            if language == "cpp":
                class_pattern = r'(?:class|struct)\s+(\w+)(?:\s*:\s*(?:public|private|protected)\s+(\w+))?\s*\{'
                for match in re.finditer(class_pattern, content, re.MULTILINE):
                    class_name = match.group(1)
                    base_class = match.group(2)
                    line_num = content[:match.start()].count('\n') + 1

                    entities.append(CodeEntity(
                        id=f"class:{file_path}:{class_name}",
                        type="class",
                        name=class_name,
                        file_path=file_path,
                        content_preview="",
                        metadata={
                            "base_class": base_class,
                            "line_start": line_num
                        }
                    ))
            else:
                # C structs
                struct_pattern = r'typedef\s+struct\s+(?:\w+\s+)?\{[^}]*\}\s*(\w+);|struct\s+(\w+)\s*\{'
                for match in re.finditer(struct_pattern, content, re.MULTILINE):
                    struct_name = match.group(1) or match.group(2)
                    line_num = content[:match.start()].count('\n') + 1

                    entities.append(CodeEntity(
                        id=f"struct:{file_path}:{struct_name}",
                        type="struct",
                        name=struct_name,
                        file_path=file_path,
                        content_preview="",
                        metadata={"line_start": line_num}
                    ))

        except Exception as e:
            logger.warning(f"Error analyzing C/C++ file {file_path}: {e}")

        return entities

    def _analyze_go_file(self, content: str, file_path: str) -> List[CodeEntity]:
        """Analyze Go files"""
        entities = []

        try:
            # Add file entity
            entities.append(CodeEntity(
                id=f"file:{file_path}",
                type="file",
                name=os.path.basename(file_path),
                file_path=file_path,
                content_preview=content[:500],
                metadata={"language": "go", "size": len(content)}
            ))

            # Extract functions
            function_pattern = r'func\s+(?:\([^)]*\)\s+)?(\w+)\s*\([^)]*\)(?:\s*\([^)]*\))?\s*\{'
            for match in re.finditer(function_pattern, content, re.MULTILINE):
                function_name = match.group(1)
                line_num = content[:match.start()].count('\n') + 1

                entities.append(CodeEntity(
                    id=f"function:{file_path}:{function_name}",
                    type="function",
                    name=function_name,
                    file_path=file_path,
                    content_preview="",
                    metadata={"line_start": line_num}
                ))

            # Extract structs
            struct_pattern = r'type\s+(\w+)\s+struct\s*\{'
            for match in re.finditer(struct_pattern, content, re.MULTILINE):
                struct_name = match.group(1)
                line_num = content[:match.start()].count('\n') + 1

                entities.append(CodeEntity(
                    id=f"struct:{file_path}:{struct_name}",
                    type="struct",
                    name=struct_name,
                    file_path=file_path,
                    content_preview="",
                    metadata={"line_start": line_num}
                ))

            # Extract interfaces
            interface_pattern = r'type\s+(\w+)\s+interface\s*\{'
            for match in re.finditer(interface_pattern, content, re.MULTILINE):
                interface_name = match.group(1)
                line_num = content[:match.start()].count('\n') + 1

                entities.append(CodeEntity(
                    id=f"interface:{file_path}:{interface_name}",
                    type="interface",
                    name=interface_name,
                    file_path=file_path,
                    content_preview="",
                    metadata={"line_start": line_num}
                ))

        except Exception as e:
            logger.warning(f"Error analyzing Go file {file_path}: {e}")

        return entities

    def _analyze_rust_file(self, content: str, file_path: str) -> List[CodeEntity]:
        """Analyze Rust files"""
        entities = []

        try:
            # Add file entity
            entities.append(CodeEntity(
                id=f"file:{file_path}",
                type="file",
                name=os.path.basename(file_path),
                file_path=file_path,
                content_preview=content[:500],
                metadata={"language": "rust", "size": len(content)}
            ))

            # Extract functions
            function_pattern = r'(?:pub\s+)?(?:async\s+)?fn\s+(\w+)\s*\([^)]*\)(?:\s*->\s*[^{]+)?\s*\{'
            for match in re.finditer(function_pattern, content, re.MULTILINE):
                function_name = match.group(1)
                line_num = content[:match.start()].count('\n') + 1

                entities.append(CodeEntity(
                    id=f"function:{file_path}:{function_name}",
                    type="function",
                    name=function_name,
                    file_path=file_path,
                    content_preview="",
                    metadata={"line_start": line_num}
                ))

            # Extract structs
            struct_pattern = r'(?:pub\s+)?struct\s+(\w+)(?:<[^>]*>)?\s*\{'
            for match in re.finditer(struct_pattern, content, re.MULTILINE):
                struct_name = match.group(1)
                line_num = content[:match.start()].count('\n') + 1

                entities.append(CodeEntity(
                    id=f"struct:{file_path}:{struct_name}",
                    type="struct",
                    name=struct_name,
                    file_path=file_path,
                    content_preview="",
                    metadata={"line_start": line_num}
                ))

            # Extract enums
            enum_pattern = r'(?:pub\s+)?enum\s+(\w+)(?:<[^>]*>)?\s*\{'
            for match in re.finditer(enum_pattern, content, re.MULTILINE):
                enum_name = match.group(1)
                line_num = content[:match.start()].count('\n') + 1

                entities.append(CodeEntity(
                    id=f"enum:{file_path}:{enum_name}",
                    type="enum",
                    name=enum_name,
                    file_path=file_path,
                    content_preview="",
                    metadata={"line_start": line_num}
                ))

            # Extract traits
            trait_pattern = r'(?:pub\s+)?trait\s+(\w+)(?:<[^>]*>)?\s*\{'
            for match in re.finditer(trait_pattern, content, re.MULTILINE):
                trait_name = match.group(1)
                line_num = content[:match.start()].count('\n') + 1

                entities.append(CodeEntity(
                    id=f"trait:{file_path}:{trait_name}",
                    type="trait",
                    name=trait_name,
                    file_path=file_path,
                    content_preview="",
                    metadata={"line_start": line_num}
                ))

        except Exception as e:
            logger.warning(f"Error analyzing Rust file {file_path}: {e}")

        return entities

    def _analyze_ruby_file(self, content: str, file_path: str) -> List[CodeEntity]:
        """Analyze Ruby files"""
        entities = []

        try:
            # Add file entity
            entities.append(CodeEntity(
                id=f"file:{file_path}",
                type="file",
                name=os.path.basename(file_path),
                file_path=file_path,
                content_preview=content[:500],
                metadata={"language": "ruby", "size": len(content)}
            ))

            # Extract classes
            class_pattern = r'class\s+(\w+)(?:\s*<\s*(\w+))?\s*$'
            for match in re.finditer(class_pattern, content, re.MULTILINE):
                class_name = match.group(1)
                superclass = match.group(2)
                line_num = content[:match.start()].count('\n') + 1

                entities.append(CodeEntity(
                    id=f"class:{file_path}:{class_name}",
                    type="class",
                    name=class_name,
                    file_path=file_path,
                    content_preview="",
                    metadata={
                        "superclass": superclass,
                        "line_start": line_num
                    }
                ))

            # Extract modules
            module_pattern = r'module\s+(\w+)\s*$'
            for match in re.finditer(module_pattern, content, re.MULTILINE):
                module_name = match.group(1)
                line_num = content[:match.start()].count('\n') + 1

                entities.append(CodeEntity(
                    id=f"module:{file_path}:{module_name}",
                    type="module",
                    name=module_name,
                    file_path=file_path,
                    content_preview="",
                    metadata={"line_start": line_num}
                ))

            # Extract methods
            method_pattern = r'def\s+(\w+)(?:\([^)]*\))?\s*$'
            for match in re.finditer(method_pattern, content, re.MULTILINE):
                method_name = match.group(1)
                line_num = content[:match.start()].count('\n') + 1

                entities.append(CodeEntity(
                    id=f"method:{file_path}:{method_name}",
                    type="method",
                    name=method_name,
                    file_path=file_path,
                    content_preview="",
                    metadata={"line_start": line_num}
                ))

        except Exception as e:
            logger.warning(f"Error analyzing Ruby file {file_path}: {e}")

        return entities

    def _analyze_csharp_file(self, content: str, file_path: str) -> List[CodeEntity]:
        """Analyze C# files"""
        entities = []

        try:
            # Add file entity
            entities.append(CodeEntity(
                id=f"file:{file_path}",
                type="file",
                name=os.path.basename(file_path),
                file_path=file_path,
                content_preview=content[:500],
                metadata={"language": "csharp", "size": len(content)}
            ))

            # Extract classes
            class_pattern = r'(?:public\s+|private\s+|protected\s+|internal\s+)?(?:abstract\s+|sealed\s+)?class\s+(\w+)(?:\s*:\s*([\w,\s]+))?\s*\{'
            for match in re.finditer(class_pattern, content, re.MULTILINE):
                class_name = match.group(1)
                inheritance = match.group(2)
                line_num = content[:match.start()].count('\n') + 1

                entities.append(CodeEntity(
                    id=f"class:{file_path}:{class_name}",
                    type="class",
                    name=class_name,
                    file_path=file_path,
                    content_preview="",
                    metadata={
                        "inheritance": inheritance.split(',') if inheritance else [],
                        "line_start": line_num
                    }
                ))

            # Extract interfaces
            interface_pattern = r'(?:public\s+|private\s+|protected\s+|internal\s+)?interface\s+(\w+)(?:\s*:\s*([\w,\s]+))?\s*\{'
            for match in re.finditer(interface_pattern, content, re.MULTILINE):
                interface_name = match.group(1)
                inheritance = match.group(2)
                line_num = content[:match.start()].count('\n') + 1

                entities.append(CodeEntity(
                    id=f"interface:{file_path}:{interface_name}",
                    type="interface",
                    name=interface_name,
                    file_path=file_path,
                    content_preview="",
                    metadata={
                        "inheritance": inheritance.split(',') if inheritance else [],
                        "line_start": line_num
                    }
                ))

            # Extract methods
            method_pattern = r'(?:public\s+|private\s+|protected\s+|internal\s+)?(?:static\s+|virtual\s+|override\s+|abstract\s+)*(?:\w+\s+)+(\w+)\s*\([^)]*\)\s*\{'
            for match in re.finditer(method_pattern, content, re.MULTILINE):
                method_name = match.group(1)
                line_num = content[:match.start()].count('\n') + 1

                # Skip common keywords
                if method_name not in ['if', 'for', 'while', 'switch', 'using', 'return']:
                    entities.append(CodeEntity(
                        id=f"method:{file_path}:{method_name}",
                        type="method",
                        name=method_name,
                        file_path=file_path,
                        content_preview="",
                        metadata={"line_start": line_num}
                    ))

        except Exception as e:
            logger.warning(f"Error analyzing C# file {file_path}: {e}")

        return entities

    def _create_class_entity(self, node: ast.ClassDef, file_path: str) -> CodeEntity:
        """Create class entity from AST node"""
        docstring = ast.get_docstring(node) or ""
        bases = [self._get_name(base) for base in node.bases]

        # Extract methods
        methods = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                methods.append(item.name)

        return CodeEntity(
            id=f"class:{file_path}:{node.name}",
            type="class",
            name=node.name,
            file_path=file_path,
            content_preview=docstring[:200],
            metadata={
                "bases": bases,
                "methods": methods,
                "line_start": node.lineno,
                "line_end": getattr(node, "end_lineno", node.lineno),
            },
        )

    def _create_function_entity(
        self, node: ast.FunctionDef, file_path: str
    ) -> CodeEntity:
        """Create function entity from AST node"""
        docstring = ast.get_docstring(node) or ""
        args = [arg.arg for arg in node.args.args]

        return CodeEntity(
            id=f"function:{file_path}:{node.name}",
            type="function",
            name=node.name,
            file_path=file_path,
            content_preview=docstring[:200],
            metadata={
                "args": args,
                "line_start": node.lineno,
                "line_end": getattr(node, "end_lineno", node.lineno),
            },
        )

    def _analyze_generic_file(self, content: str, file_path: str) -> List[CodeEntity]:
        """Basic analysis for non-Python files"""
        entities = []

        # Add file entity
        entities.append(
            CodeEntity(
                id=f"file:{file_path}",
                type="file",
                name=os.path.basename(file_path),
                file_path=file_path,
                content_preview=content[:500],
                metadata={
                    "language": self._detect_language(file_path),
                    "size": len(content),
                },
            )
        )

        # Extract basic patterns (functions, classes, etc.)
        entities.extend(self._extract_basic_patterns(content, file_path))

        return entities

    def _extract_basic_patterns(self, content: str, file_path: str) -> List[CodeEntity]:
        """Extract basic code patterns using regex"""
        entities = []

        # Function patterns for different languages
        patterns = {
            "function": [
                r"function\s+(\w+)\s*\(",  # JavaScript
                r"def\s+(\w+)\s*\(",  # Python, Ruby
                r"func\s+(?:\([^)]*\)\s+)?(\w+)\s*\(",  # Go
                r"fn\s+(\w+)\s*\(",  # Rust
                r"(?:public\s+|private\s+|protected\s+)?function\s+(\w+)\s*\(",  # PHP
                r"(?:public\s+|private\s+|protected\s+|static\s+)*(?:\w+\s+)+(\w+)\s*\([^)]*\)\s*\{",  # Java, C#, C++
                r"(?:static\s+|inline\s+|extern\s+)*(?:\w+\s+\*?\s*)+(\w+)\s*\([^)]*\)\s*\{",  # C/C++
                r"sub\s+(\w+)\s*\{",  # Perl
                r"(\w+)\s*::\s*proc\s*\{",  # Tcl
            ],
            "class": [
                r"class\s+(\w+)",  # Python, JavaScript, Java, C#, PHP, Ruby
                r"struct\s+(\w+)",  # Go, Rust, C++, C
                r"interface\s+(\w+)",  # Go, TypeScript, Java, C#
                r"trait\s+(\w+)",  # Rust, PHP
                r"enum\s+(\w+)",  # Java, C#, Rust, Swift
                r"module\s+(\w+)",  # Ruby, Elixir
                r"namespace\s+(\w+)",  # C#, C++
                r"package\s+(\w+)",  # Java, Go
                r"type\s+(\w+)\s+(?:struct|interface)",  # Go
                r"(?:abstract\s+)?class\s+(\w+)",  # PHP, Java
            ],
            "method": [
                r"(?:public\s+|private\s+|protected\s+)?(?:static\s+)?(?:function\s+)?(\w+)\s*\([^)]*\)\s*\{",  # General
                r"(\w+)\s*:\s*function\s*\(",  # JavaScript object methods
                r"(\w+)\s*=\s*\([^)]*\)\s*=>",  # Arrow functions
            ]
        }

        for entity_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                matches = re.finditer(pattern, content, re.MULTILINE)
                for match in matches:
                    name = match.group(1)
                    line_num = content[: match.start()].count("\n") + 1

                    entities.append(
                        CodeEntity(
                            id=f"{entity_type}:{file_path}:{name}",
                            type=entity_type,
                            name=name,
                            file_path=file_path,
                            content_preview="",
                            metadata={"line_start": line_num},
                        )
                    )

        return entities

    def _extract_relevant_entities(
        self, code_graph: CodeGraph, query: str, focus_files: Optional[List[str]] = None
    ) -> List[CodeEntity]:
        """Extract entities relevant to the query"""
        relevant = []
        query_lower = query.lower()

        # Extract keywords from query
        keywords = self._extract_keywords(query)

        for entity in code_graph.entities:
            relevance_score = 0

            # File filtering
            if focus_files and entity.file_path not in focus_files:
                continue

            # If we have focus_files, include all entities from those files
            if focus_files and entity.file_path in focus_files:
                relevance_score += 1  # Base score for being in focus files

            # Name matching
            if any(keyword in entity.name.lower() for keyword in keywords):
                relevance_score += 3

            # Content matching
            if entity.content_preview and any(
                keyword in entity.content_preview.lower() for keyword in keywords
            ):
                relevance_score += 2

            # File path matching
            if any(keyword in entity.file_path.lower() for keyword in keywords):
                relevance_score += 1

            # Include entity if it has any relevance score or if no keywords were found
            if relevance_score > 0 or (not keywords and not focus_files):
                entity.metadata["relevance_score"] = relevance_score
                relevant.append(entity)

        # Sort by relevance score
        relevant.sort(key=lambda x: x.metadata.get("relevance_score", 0), reverse=True)

        return relevant[:50]  # Limit to top 50 entities

    def _extract_keywords(self, query: str) -> List[str]:
        """Extract keywords from query"""
        # Remove common stop words
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
        }

        # Extract words
        words = re.findall(r"\b\w+\b", query.lower())
        keywords = [word for word in words if word not in stop_words and len(word) > 2]

        return keywords

    async def _analyze_files(
        self, repo_path: str, entities: List[CodeEntity], max_files: int = 10
    ) -> List[FileAnalysis]:
        """Analyze specific files in detail"""
        file_analyses = []
        processed_files = set()

        for entity in entities:
            if len(file_analyses) >= max_files:
                break

            if entity.file_path in processed_files:
                continue

            file_path = os.path.join(repo_path, entity.file_path)
            if os.path.exists(file_path):
                analysis = await self._analyze_single_file(file_path, entity.file_path)
                if analysis:
                    file_analyses.append(analysis)
                    processed_files.add(entity.file_path)

        return file_analyses

    async def _analyze_single_file(
        self, file_path: str, relative_path: str
    ) -> Optional[FileAnalysis]:
        """Analyze a single file in detail"""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

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
                },
            )

        except Exception as e:
            logger.warning(f"Failed to analyze file {file_path}: {e}")
            return None

    def _extract_file_structure(self, content: str, file_path: str) -> Dict[str, Any]:
        """Extract file structure summary"""
        structure = {"classes": [], "functions": [], "imports": [], "exports": []}

        if file_path.endswith(".py"):
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        structure["classes"].append(
                            {
                                "name": node.name,
                                "line": node.lineno,
                                "methods": [
                                    item.name
                                    for item in node.body
                                    if isinstance(item, ast.FunctionDef)
                                ],
                            }
                        )
                    elif isinstance(node, ast.FunctionDef):
                        structure["functions"].append(
                            {
                                "name": node.name,
                                "line": node.lineno,
                                "args": [arg.arg for arg in node.args.args],
                            }
                        )
                    elif isinstance(node, (ast.Import, ast.ImportFrom)):
                        structure["imports"].append(self._format_import(node))
            except:
                pass

        return structure

    def _extract_dependencies(self, content: str, file_path: str) -> List[str]:
        """Extract file dependencies"""
        dependencies = []

        # Python imports
        if file_path.endswith(".py"):
            import_patterns = [r"from\s+(\S+)\s+import", r"import\s+(\S+)"]
            for pattern in import_patterns:
                matches = re.findall(pattern, content)
                dependencies.extend(matches)

        # JavaScript/TypeScript imports
        elif file_path.endswith((".js", ".ts")):
            import_patterns = [
                r'import.*from\s+[\'"]([^\'"]+)[\'"]',
                r'require\([\'"]([^\'"]+)[\'"]\)',
            ]
            for pattern in import_patterns:
                matches = re.findall(pattern, content)
                dependencies.extend(matches)

        return list(set(dependencies))  # Remove duplicates

    def _extract_relations(
        self, code_graph: CodeGraph, entities: List[CodeEntity]
    ) -> List[CodeRelation]:
        """Extract relationships between code entities"""
        relations = []

        # Build entity lookup
        entity_lookup = {entity.id: entity for entity in entities}

        # Extract relations from graph data
        if code_graph.graph_data and "edges" in code_graph.graph_data:
            for edge in code_graph.graph_data["edges"]:
                source_id = edge.get("source")
                target_id = edge.get("target")
                relation_type = edge.get("type", "unknown")

                if source_id in entity_lookup and target_id in entity_lookup:
                    relations.append(
                        CodeRelation(
                            source_entity_id=source_id,
                            target_entity_id=target_id,
                            relation_type=relation_type,
                            metadata=edge,
                        )
                    )

        return relations

    def _generate_context_summary(
        self,
        code_graph: CodeGraph,
        entities: List[CodeEntity],
        file_analyses: List[FileAnalysis],
    ) -> str:
        """Generate human-readable context summary"""
        summary_parts = []

        # Repository overview
        summary_parts.append(
            f"Repository contains {len(code_graph.files)} files with {len(code_graph.entities)} code entities."
        )

        # File types
        file_types = {}
        for file_path in code_graph.files:
            ext = Path(file_path).suffix
            file_types[ext] = file_types.get(ext, 0) + 1

        if file_types:
            summary_parts.append(
                f"File types: {', '.join(f'{ext}({count})' for ext, count in file_types.items())}"
            )

        # Relevant entities
        if entities:
            entity_types = {}
            for entity in entities[:10]:  # Top 10
                entity_types[entity.type] = entity_types.get(entity.type, 0) + 1

            summary_parts.append(
                f"Relevant entities: {', '.join(f'{t}({c})' for t, c in entity_types.items())}"
            )

        # Key files
        if file_analyses:
            key_files = [fa.file_path for fa in file_analyses[:5]]
            summary_parts.append(f"Key files: {', '.join(key_files)}")

        return "\n".join(summary_parts)

    # Helper methods
    def _get_name(self, node: ast.AST) -> str:
        """Get name from AST node"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        else:
            return str(node)

    def _format_import(self, node) -> str:
        """Format import statement"""
        if isinstance(node, ast.Import):
            return ", ".join(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = ", ".join(alias.name for alias in node.names)
            return f"{module}: {names}"
        return ""

    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension"""
        ext = Path(file_path).suffix.lower()
        language_map = {
            # Python
            ".py": "python", ".pyx": "python", ".pyi": "python",
            # JavaScript/TypeScript
            ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
            ".ts": "typescript", ".tsx": "typescript",
            # Java/Kotlin/Scala
            ".java": "java", ".kt": "kotlin", ".scala": "scala",
            # C/C++
            ".c": "c", ".h": "c",
            ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp", ".hxx": "cpp",
            # Go
            ".go": "go",
            # Rust
            ".rs": "rust",
            # PHP
            ".php": "php", ".php3": "php", ".php4": "php", ".php5": "php", ".phtml": "php",
            # Ruby
            ".rb": "ruby", ".rbw": "ruby",
            # C#
            ".cs": "csharp",
            # Swift
            ".swift": "swift",
            # Objective-C
            ".m": "objective-c", ".mm": "objective-c",
            # Dart
            ".dart": "dart",
            # Lua
            ".lua": "lua",
            # Shell
            ".sh": "shell", ".bash": "shell", ".zsh": "shell", ".fish": "shell",
            # SQL
            ".sql": "sql",
            # R
            ".r": "r", ".R": "r",
            # Perl
            ".pl": "perl", ".pm": "perl",
            # Haskell
            ".hs": "haskell",
            # Erlang/Elixir
            ".erl": "erlang", ".ex": "elixir", ".exs": "elixir",
            # Clojure
            ".clj": "clojure", ".cljs": "clojure", ".cljc": "clojure",
            # F#
            ".fs": "fsharp", ".fsx": "fsharp",
            # Visual Basic
            ".vb": "vb",
            # PowerShell
            ".ps1": "powershell", ".psm1": "powershell",
        }
        return language_map.get(ext, "unknown")

    def _add_file_to_graph(
        self, graph: nx.DiGraph, file_path: str, entities: List[CodeEntity]
    ):
        """Add file and its entities to the graph"""
        file_node = f"file:{file_path}"
        graph.add_node(file_node, type="file", name=os.path.basename(file_path))

        for entity in entities:
            if entity.id != file_node:  # Don't add file to itself
                graph.add_node(entity.id, **entity.metadata)
                graph.add_edge(file_node, entity.id, type="contains")

    def _serialize_graph(self, graph: nx.DiGraph) -> Dict[str, Any]:
        """Serialize NetworkX graph to dictionary"""
        return {
            "nodes": [{"id": node, **data} for node, data in graph.nodes(data=True)],
            "edges": [
                {"source": u, "target": v, **data}
                for u, v, data in graph.edges(data=True)
            ],
        }

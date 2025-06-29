"""
GPU-Enhanced Analyzer for CGM MCP Server
Integrates GPU acceleration with existing analysis capabilities
"""

import asyncio
import time
from typing import List, Dict, Any, Optional
from loguru import logger

from .analyzer import CGMAnalyzer
from .gpu_accelerator import EntityMatcher, TextProcessor, GPUAcceleratorConfig
from ..models import CodeAnalysisRequest, CodeAnalysisResponse, CodeEntity


class GPUEnhancedAnalyzer(CGMAnalyzer):
    """
    Enhanced CGM analyzer with GPU acceleration for entity matching and text processing
    """
    
    def __init__(self, gpu_config: GPUAcceleratorConfig = None):
        super().__init__()
        
        # Initialize GPU accelerators
        self.gpu_config = gpu_config or GPUAcceleratorConfig()
        self.entity_matcher = EntityMatcher(self.gpu_config)
        self.text_processor = TextProcessor(self.gpu_config)
        
        # Performance tracking
        self.performance_stats = {
            "gpu_entity_matches": 0,
            "gpu_text_analyses": 0,
            "total_gpu_time": 0.0,
            "total_cpu_time": 0.0,
            "gpu_cache_hits": 0,
            "gpu_cache_misses": 0
        }
        
        logger.info(f"GPU Enhanced Analyzer initialized - GPU available: {self.entity_matcher.gpu_available}")
    
    def get_gpu_stats(self) -> Dict[str, Any]:
        """Get GPU performance and memory statistics"""
        stats = {
            "performance": self.performance_stats.copy(),
            "memory": self.entity_matcher.get_memory_usage(),
            "config": {
                "use_gpu": self.gpu_config.use_gpu,
                "batch_size": self.gpu_config.batch_size,
                "cache_embeddings": self.gpu_config.cache_embeddings,
                "similarity_threshold": self.gpu_config.similarity_threshold
            }
        }
        
        # Calculate efficiency metrics
        total_time = self.performance_stats["total_gpu_time"] + self.performance_stats["total_cpu_time"]
        if total_time > 0:
            stats["performance"]["gpu_time_percentage"] = (
                self.performance_stats["total_gpu_time"] / total_time * 100
            )
        
        cache_requests = self.performance_stats["gpu_cache_hits"] + self.performance_stats["gpu_cache_misses"]
        if cache_requests > 0:
            stats["performance"]["cache_hit_rate"] = (
                self.performance_stats["gpu_cache_hits"] / cache_requests * 100
            )
        
        return stats
    
    def clear_gpu_caches(self):
        """Clear GPU caches to free memory"""
        self.entity_matcher.clear_caches()
        self.text_processor.clear_caches()
        logger.info("GPU caches cleared")
    
    async def analyze_repository(self, request: CodeAnalysisRequest) -> CodeAnalysisResponse:
        """Enhanced repository analysis with GPU acceleration"""
        start_time = time.time()
        
        # Use parent class for initial analysis
        response = await super().analyze_repository(request)
        
        # Enhance with GPU-accelerated entity matching if we have a query
        if request.query and response.relevant_entities:
            response = await self._enhance_with_gpu_matching(response, request.query)
        
        # GPU-accelerated text analysis for file contents
        if response.file_analyses:
            await self._enhance_with_gpu_text_analysis(response)
        
        total_time = time.time() - start_time
        self.performance_stats["total_cpu_time"] += total_time
        
        logger.info(f"GPU-enhanced analysis completed in {total_time:.3f}s")
        return response
    
    async def _enhance_with_gpu_matching(self, response: CodeAnalysisResponse, 
                                       query: str) -> CodeAnalysisResponse:
        """Enhance entity matching with GPU acceleration"""
        start_time = time.time()
        
        try:
            # Convert entities to dictionaries for GPU processing
            entity_dicts = []
            for entity in response.relevant_entities:
                entity_dict = {
                    "name": entity.name,
                    "description": getattr(entity, 'description', ''),
                    "content_preview": getattr(entity, 'content_preview', ''),
                    "type": entity.type,
                    "file_path": entity.file_path
                }
                entity_dicts.append(entity_dict)
            
            # GPU-accelerated similarity matching
            similar_entities = self.entity_matcher.find_similar_entities(
                entity_dicts, query, top_k=min(50, len(entity_dicts))
            )
            
            # Convert back to CodeEntity objects with similarity scores
            enhanced_entities = []
            for entity_dict, similarity_score in similar_entities:
                # Find original entity
                original_entity = None
                for entity in response.relevant_entities:
                    if (entity.name == entity_dict["name"] and 
                        entity.file_path == entity_dict["file_path"]):
                        original_entity = entity
                        break
                
                if original_entity:
                    # Add similarity score as metadata
                    if not hasattr(original_entity, 'metadata'):
                        original_entity.metadata = {}
                    original_entity.metadata['gpu_similarity_score'] = similarity_score
                    enhanced_entities.append(original_entity)
            
            # Update response with GPU-enhanced entities
            response.relevant_entities = enhanced_entities
            
            # Update performance stats
            gpu_time = time.time() - start_time
            self.performance_stats["total_gpu_time"] += gpu_time
            self.performance_stats["gpu_entity_matches"] += 1
            
            logger.debug(f"GPU entity matching completed in {gpu_time:.3f}s "
                        f"({len(enhanced_entities)} entities)")
            
        except Exception as e:
            logger.warning(f"GPU entity matching failed, falling back to CPU: {e}")
            # Keep original entities if GPU processing fails
        
        return response
    
    async def _enhance_with_gpu_text_analysis(self, response: CodeAnalysisResponse):
        """Enhance file analysis with GPU-accelerated text processing"""
        start_time = time.time()
        
        try:
            # Extract file contents for batch processing
            file_contents = []
            for file_analysis in response.file_analyses:
                file_contents.append(file_analysis.content)
            
            # GPU-accelerated batch text analysis
            text_stats = self.text_processor.batch_text_analysis(file_contents)
            
            # Add GPU analysis results to response metadata
            if not hasattr(response, 'metadata') or response.metadata is None:
                response.metadata = {}

            response.metadata['gpu_text_analysis'] = text_stats
            
            # Add individual file statistics
            for i, file_analysis in enumerate(response.file_analyses):
                if not hasattr(file_analysis, 'metadata'):
                    file_analysis.metadata = {}
                
                file_analysis.metadata['gpu_processed'] = True
                if i < len(file_contents):
                    file_analysis.metadata['content_length'] = len(file_contents[i])
            
            # Update performance stats
            gpu_time = time.time() - start_time
            self.performance_stats["total_gpu_time"] += gpu_time
            self.performance_stats["gpu_text_analyses"] += 1
            
            logger.debug(f"GPU text analysis completed in {gpu_time:.3f}s "
                        f"({len(file_contents)} files)")
            
        except Exception as e:
            logger.warning(f"GPU text analysis failed: {e}")
    
    async def find_related_entities_gpu(self, entities: List[CodeEntity], 
                                      query: str, top_k: int = 20) -> List[CodeEntity]:
        """Find related entities using GPU acceleration"""
        start_time = time.time()
        
        try:
            # Convert to dictionaries
            entity_dicts = []
            for entity in entities:
                entity_dict = {
                    "name": entity.name,
                    "description": getattr(entity, 'description', ''),
                    "content_preview": getattr(entity, 'content_preview', ''),
                    "type": entity.type,
                    "file_path": entity.file_path
                }
                entity_dicts.append(entity_dict)
            
            # GPU-accelerated matching
            similar_entities = self.entity_matcher.find_similar_entities(
                entity_dicts, query, top_k=top_k
            )
            
            # Convert back to CodeEntity objects
            result_entities = []
            for entity_dict, similarity_score in similar_entities:
                # Find original entity
                for entity in entities:
                    if (entity.name == entity_dict["name"] and 
                        entity.file_path == entity_dict["file_path"]):
                        # Add similarity score
                        if not hasattr(entity, 'metadata'):
                            entity.metadata = {}
                        entity.metadata['similarity_score'] = similarity_score
                        result_entities.append(entity)
                        break
            
            gpu_time = time.time() - start_time
            self.performance_stats["total_gpu_time"] += gpu_time
            
            logger.debug(f"GPU entity search completed in {gpu_time:.3f}s")
            return result_entities
            
        except Exception as e:
            logger.warning(f"GPU entity search failed, falling back to CPU: {e}")
            # Fallback to CPU-based search
            return self._cpu_find_related_entities(entities, query, top_k)
    
    def _cpu_find_related_entities(self, entities: List[CodeEntity], 
                                 query: str, top_k: int) -> List[CodeEntity]:
        """CPU fallback for entity search"""
        start_time = time.time()
        
        # Simple keyword-based matching as fallback
        query_words = query.lower().split()
        scored_entities = []
        
        for entity in entities:
            score = 0
            entity_text = f"{entity.name} {getattr(entity, 'description', '')}".lower()
            
            for word in query_words:
                if word in entity_text:
                    score += 1
            
            if score > 0:
                if not hasattr(entity, 'metadata'):
                    entity.metadata = {}
                entity.metadata['similarity_score'] = score / len(query_words)
                scored_entities.append((entity, score))
        
        # Sort by score and return top-k
        scored_entities.sort(key=lambda x: x[1], reverse=True)
        result_entities = [entity for entity, _ in scored_entities[:top_k]]
        
        cpu_time = time.time() - start_time
        self.performance_stats["total_cpu_time"] += cpu_time
        
        return result_entities

    async def _analyze_single_file_async(self, file_path: str, relative_path: str):
        """Async wrapper for single file analysis"""
        try:
            # Use parent class method for file analysis
            return await asyncio.get_event_loop().run_in_executor(
                None,
                self._analyze_single_file,
                file_path,
                relative_path
            )
        except Exception as e:
            logger.warning(f"Async file analysis failed for {relative_path}: {e}")
            return None

    async def batch_analyze_files_gpu(self, file_paths: List[str],
                                    contents: List[str]) -> Dict[str, Any]:
        """Batch analyze files with GPU acceleration"""
        start_time = time.time()
        
        try:
            # GPU-accelerated text analysis
            text_stats = self.text_processor.batch_text_analysis(contents)
            
            # Pattern searching for common code patterns
            code_patterns = [
                "class ", "def ", "import ", "from ", "if __name__",
                "async def", "await ", "return ", "raise ", "try:"
            ]
            
            pattern_results = self.text_processor.batch_pattern_search(contents, code_patterns)
            
            gpu_time = time.time() - start_time
            self.performance_stats["total_gpu_time"] += gpu_time
            
            return {
                "text_statistics": text_stats,
                "pattern_matches": pattern_results,
                "processing_time": gpu_time,
                "files_processed": len(file_paths),
                "gpu_accelerated": True
            }
            
        except Exception as e:
            logger.warning(f"GPU batch analysis failed: {e}")
            return {
                "error": str(e),
                "gpu_accelerated": False,
                "files_processed": len(file_paths)
            }

"""
GPU Accelerator for CGM MCP Server
Provides GPU-accelerated entity matching and text processing
"""

import time
import hashlib
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from loguru import logger

# GPU libraries with fallback
try:
    import torch
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available - GPU acceleration disabled")

try:
    import cupy as cp
    CUPY_AVAILABLE = True
except ImportError:
    CUPY_AVAILABLE = False
    # Only warn if we're on a platform that could benefit from CuPy
    import platform
    if platform.system() == "Linux" or (platform.system() == "Windows" and "NVIDIA" in str(platform.processor()).upper()):
        logger.warning("CuPy not available - some GPU features disabled")
    else:
        logger.debug("CuPy not available (not needed for this platform)")


@dataclass
class GPUAcceleratorConfig:
    """Configuration for GPU acceleration"""
    use_gpu: bool = True
    batch_size: int = 1024
    max_sequence_length: int = 512
    similarity_threshold: float = 0.1
    cache_embeddings: bool = True
    gpu_memory_fraction: float = 0.8


class GPUAccelerator:
    """Main GPU acceleration class for CGM operations"""
    
    def __init__(self, config: GPUAcceleratorConfig = None):
        self.config = config or GPUAcceleratorConfig()
        self._setup_device()
        self._setup_caches()
        
    def _setup_device(self):
        """Setup GPU device and configuration with multi-platform support"""
        self.torch_available = TORCH_AVAILABLE
        self.cupy_available = CUPY_AVAILABLE
        self.platform = self._detect_gpu_platform()

        if not self.torch_available or not self.config.use_gpu:
            self._setup_cpu_fallback()
            return

        if self.platform == "Apple Silicon":
            self._setup_apple_silicon()
        elif self.platform == "NVIDIA CUDA":
            self._setup_nvidia_cuda()
        elif self.platform == "AMD ROCm":
            self._setup_amd_rocm()
        elif self.platform == "AMD DirectML":
            self._setup_amd_directml()
        else:
            self._setup_cpu_fallback()

    def _detect_gpu_platform(self) -> str:
        """Detect available GPU platform"""
        if not self.torch_available:
            return "CPU"

        # Check Apple Silicon (MPS)
        if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return "Apple Silicon"

        # Check NVIDIA CUDA
        if torch.cuda.is_available():
            try:
                gpu_name = torch.cuda.get_device_name(0).upper()
                if any(amd_keyword in gpu_name for amd_keyword in ['AMD', 'RADEON', 'RX']):
                    return "AMD ROCm"
                else:
                    return "NVIDIA CUDA"
            except:
                return "NVIDIA CUDA"

        # Check AMD DirectML (Windows)
        try:
            import torch_directml
            if torch_directml.is_available():
                return "AMD DirectML"
        except ImportError:
            pass

        return "CPU"

    def _setup_apple_silicon(self):
        """Setup Apple Silicon (M1/M2/M3) GPU"""
        try:
            self.device = torch.device('mps')
            self.gpu_available = True

            # Apple Silicon specific optimizations
            if hasattr(torch.mps, 'set_per_process_memory_fraction'):
                torch.mps.set_per_process_memory_fraction(self.config.gpu_memory_fraction)

            logger.info("Apple Silicon GPU acceleration enabled")
            logger.info("Using Metal Performance Shaders (MPS)")

        except Exception as e:
            logger.warning(f"Failed to setup Apple Silicon GPU: {e}")
            self._setup_cpu_fallback()

    def _setup_nvidia_cuda(self):
        """Setup NVIDIA CUDA GPU"""
        try:
            self.device = torch.device('cuda')
            self.gpu_available = True

            # Set memory fraction
            if hasattr(torch.cuda, 'set_memory_fraction'):
                torch.cuda.set_memory_fraction(self.config.gpu_memory_fraction)

            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9

            logger.info(f"NVIDIA CUDA GPU acceleration enabled: {gpu_name}")
            logger.info(f"GPU memory: {gpu_memory:.1f}GB")

        except Exception as e:
            logger.warning(f"Failed to setup NVIDIA CUDA: {e}")
            self._setup_cpu_fallback()

    def _setup_amd_rocm(self):
        """Setup AMD GPU with ROCm (Linux)"""
        try:
            self.device = torch.device('cuda')  # ROCm uses CUDA interface
            self.gpu_available = True

            gpu_name = torch.cuda.get_device_name(0)
            logger.info(f"AMD ROCm GPU acceleration enabled: {gpu_name}")
            logger.info("Using ROCm backend")

        except Exception as e:
            logger.warning(f"Failed to setup AMD ROCm: {e}")
            self._setup_cpu_fallback()

    def _setup_amd_directml(self):
        """Setup AMD GPU with DirectML (Windows)"""
        try:
            import torch_directml
            self.device = torch_directml.device()
            self.gpu_available = True

            logger.info("AMD DirectML GPU acceleration enabled")
            logger.info("Using DirectML backend")

        except Exception as e:
            logger.warning(f"Failed to setup AMD DirectML: {e}")
            self._setup_cpu_fallback()

    def _setup_cpu_fallback(self):
        """Setup CPU fallback"""
        self.device = torch.device('cpu')
        self.gpu_available = False
        self.platform = "CPU"
        logger.info("Using CPU for computations")
    
    def _setup_caches(self):
        """Setup embedding and computation caches"""
        self.embedding_cache = {}
        self.similarity_cache = {}
        self.text_stats_cache = {}
        
    def clear_caches(self):
        """Clear all caches to free memory on all platforms"""
        self.embedding_cache.clear()
        self.similarity_cache.clear()
        self.text_stats_cache.clear()

        if self.gpu_available:
            self._clear_gpu_memory()

    def _clear_gpu_memory(self):
        """Clear GPU memory based on platform"""
        try:
            if self.platform == "Apple Silicon":
                if hasattr(torch.mps, 'empty_cache'):
                    torch.mps.empty_cache()
                    logger.debug("Apple Silicon GPU cache cleared")
            elif self.platform in ["NVIDIA CUDA", "AMD ROCm"]:
                torch.cuda.empty_cache()
                logger.debug(f"{self.platform} GPU cache cleared")
            elif self.platform == "AMD DirectML":
                # DirectML doesn't have explicit cache clearing
                logger.debug("DirectML cache clearing not available")
        except Exception as e:
            logger.warning(f"Failed to clear GPU cache: {e}")
    
    def get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage statistics for all platforms"""
        stats = {
            "cache_size": len(self.embedding_cache),
            "gpu_available": self.gpu_available,
            "platform": self.platform
        }

        if self.gpu_available:
            if self.platform == "Apple Silicon":
                stats.update(self._get_apple_silicon_memory())
            elif self.platform in ["NVIDIA CUDA", "AMD ROCm"]:
                stats.update(self._get_cuda_memory())
            elif self.platform == "AMD DirectML":
                stats.update(self._get_directml_memory())

        return stats

    def _get_apple_silicon_memory(self) -> Dict[str, float]:
        """Get Apple Silicon memory statistics"""
        try:
            if hasattr(torch.mps, 'current_allocated_memory'):
                allocated = torch.mps.current_allocated_memory() / 1e9
                return {
                    "gpu_memory_allocated": allocated,
                    "gpu_memory_type": "Unified Memory",
                    "backend": "Metal Performance Shaders"
                }
        except:
            pass

        return {
            "gpu_memory_allocated": 0.0,
            "gpu_memory_type": "Unified Memory",
            "backend": "Metal Performance Shaders"
        }

    def _get_cuda_memory(self) -> Dict[str, float]:
        """Get CUDA memory statistics (NVIDIA/AMD ROCm)"""
        try:
            return {
                "gpu_memory_allocated": torch.cuda.memory_allocated() / 1e9,
                "gpu_memory_reserved": torch.cuda.memory_reserved() / 1e9,
                "gpu_memory_free": (torch.cuda.get_device_properties(0).total_memory -
                                   torch.cuda.memory_reserved()) / 1e9,
                "backend": "CUDA" if self.platform == "NVIDIA CUDA" else "ROCm"
            }
        except:
            return {"backend": "CUDA/ROCm", "gpu_memory_allocated": 0.0}

    def _get_directml_memory(self) -> Dict[str, float]:
        """Get DirectML memory statistics"""
        return {
            "gpu_memory_allocated": 0.0,  # DirectML doesn't expose detailed memory info
            "backend": "DirectML",
            "note": "DirectML memory info not available"
        }


class EntityMatcher(GPUAccelerator):
    """GPU-accelerated entity matching and similarity computation"""
    
    def __init__(self, config: GPUAcceleratorConfig = None):
        super().__init__(config)
        self.vocab_size = 256  # ASCII character set
        
    def _text_to_tensor(self, texts: List[str]) -> torch.Tensor:
        """Convert texts to tensor representation"""
        if not texts:
            return torch.empty(0, self.vocab_size, device=self.device)
        
        max_len = min(max(len(text) for text in texts), self.config.max_sequence_length)
        
        # Character-level encoding with frequency
        vectors = torch.zeros(len(texts), self.vocab_size, device=self.device)
        
        for i, text in enumerate(texts):
            char_counts = torch.zeros(self.vocab_size, device=self.device)
            for char in text[:max_len]:
                char_idx = ord(char) % self.vocab_size
                char_counts[char_idx] += 1.0
            
            # Normalize by text length
            if len(text) > 0:
                char_counts /= len(text)
            
            vectors[i] = char_counts
        
        return vectors
    
    def _get_embedding_cache_key(self, text: str) -> str:
        """Generate cache key for text embedding"""
        return hashlib.md5(text.encode()).hexdigest()
    
    def embed_texts(self, texts: List[str]) -> torch.Tensor:
        """Convert texts to embeddings with caching"""
        if not self.torch_available:
            return self._cpu_embed_texts(texts)
        
        embeddings = []
        uncached_texts = []
        uncached_indices = []
        
        # Check cache first
        for i, text in enumerate(texts):
            if self.config.cache_embeddings:
                cache_key = self._get_embedding_cache_key(text)
                if cache_key in self.embedding_cache:
                    embeddings.append(self.embedding_cache[cache_key])
                    continue
            
            uncached_texts.append(text)
            uncached_indices.append(i)
        
        # Process uncached texts
        if uncached_texts:
            new_embeddings = self._text_to_tensor(uncached_texts)
            
            # Cache new embeddings
            if self.config.cache_embeddings:
                for text, embedding in zip(uncached_texts, new_embeddings):
                    cache_key = self._get_embedding_cache_key(text)
                    self.embedding_cache[cache_key] = embedding.clone()
            
            # Merge with cached embeddings
            if embeddings:
                # Create full tensor and fill in embeddings
                full_embeddings = torch.zeros(len(texts), self.vocab_size, device=self.device)
                
                cached_idx = 0
                uncached_idx = 0
                
                for i in range(len(texts)):
                    if i in uncached_indices:
                        full_embeddings[i] = new_embeddings[uncached_idx]
                        uncached_idx += 1
                    else:
                        full_embeddings[i] = embeddings[cached_idx]
                        cached_idx += 1
                
                return full_embeddings
            else:
                return new_embeddings
        else:
            # All embeddings were cached
            return torch.stack(embeddings)
    
    def _cpu_embed_texts(self, texts: List[str]) -> np.ndarray:
        """CPU fallback for text embedding"""
        if not texts:
            return np.empty((0, self.vocab_size))
        
        vectors = np.zeros((len(texts), self.vocab_size))
        
        for i, text in enumerate(texts):
            char_counts = np.zeros(self.vocab_size)
            for char in text[:self.config.max_sequence_length]:
                char_idx = ord(char) % self.vocab_size
                char_counts[char_idx] += 1.0
            
            if len(text) > 0:
                char_counts /= len(text)
            
            vectors[i] = char_counts
        
        return vectors
    
    def compute_similarities(self, entity_embeddings: torch.Tensor, 
                           query_embedding: torch.Tensor) -> torch.Tensor:
        """Compute cosine similarities between entities and query"""
        if not self.torch_available:
            return self._cpu_compute_similarities(entity_embeddings, query_embedding)
        
        # Normalize embeddings
        entity_norm = F.normalize(entity_embeddings, p=2, dim=1)
        query_norm = F.normalize(query_embedding.unsqueeze(0), p=2, dim=1)
        
        # Compute cosine similarity
        similarities = torch.mm(entity_norm, query_norm.t()).squeeze()
        
        # Handle single entity case
        if similarities.dim() == 0:
            similarities = similarities.unsqueeze(0)
        
        return similarities
    
    def _cpu_compute_similarities(self, entity_embeddings: np.ndarray, 
                                query_embedding: np.ndarray) -> np.ndarray:
        """CPU fallback for similarity computation"""
        # Normalize embeddings
        entity_norms = np.linalg.norm(entity_embeddings, axis=1, keepdims=True)
        entity_norms[entity_norms == 0] = 1  # Avoid division by zero
        entity_norm = entity_embeddings / entity_norms
        
        query_norm_val = np.linalg.norm(query_embedding)
        if query_norm_val == 0:
            query_norm_val = 1
        query_norm = query_embedding / query_norm_val
        
        # Compute cosine similarity
        similarities = np.dot(entity_norm, query_norm)
        return similarities
    
    def find_similar_entities(self, entities: List[Dict[str, Any]], 
                            query: str, top_k: int = 50) -> List[Tuple[Dict[str, Any], float]]:
        """Find most similar entities to query with GPU acceleration"""
        if not entities:
            return []
        
        start_time = time.time()
        
        # Extract entity texts
        entity_texts = []
        for entity in entities:
            text_parts = []
            if 'name' in entity:
                text_parts.append(str(entity['name']))
            if 'description' in entity:
                text_parts.append(str(entity['description']))
            if 'content_preview' in entity:
                text_parts.append(str(entity['content_preview']))
            
            entity_texts.append(' '.join(text_parts))
        
        # Generate embeddings
        entity_embeddings = self.embed_texts(entity_texts)
        query_embedding = self.embed_texts([query])[0]
        
        # Compute similarities
        similarities = self.compute_similarities(entity_embeddings, query_embedding)
        
        # Convert to CPU for sorting if needed
        if self.torch_available and similarities.is_cuda:
            similarities_cpu = similarities.cpu()
        else:
            similarities_cpu = similarities
        
        # Get top-k indices
        if len(similarities_cpu) <= top_k:
            if self.torch_available:
                top_indices = torch.argsort(similarities_cpu, descending=True)
            else:
                top_indices = np.argsort(similarities_cpu)[::-1]
        else:
            if self.torch_available:
                top_indices = torch.topk(similarities_cpu, k=top_k).indices
            else:
                top_indices = np.argpartition(similarities_cpu, -top_k)[-top_k:]
                top_indices = top_indices[np.argsort(similarities_cpu[top_indices])[::-1]]
        
        # Filter by threshold and create results
        results = []
        for idx in top_indices:
            idx_val = int(idx)
            similarity_score = float(similarities_cpu[idx_val])
            
            if similarity_score >= self.config.similarity_threshold:
                results.append((entities[idx_val], similarity_score))
        
        processing_time = time.time() - start_time
        logger.debug(f"Entity matching completed in {processing_time:.3f}s "
                    f"({len(entities)} entities, {len(results)} matches)")
        
        return results


class TextProcessor(GPUAccelerator):
    """GPU-accelerated text processing operations"""
    
    def __init__(self, config: GPUAcceleratorConfig = None):
        super().__init__(config)
    
    def batch_text_analysis(self, texts: List[str]) -> Dict[str, Any]:
        """Perform batch text analysis with GPU acceleration"""
        if not texts:
            return {"num_texts": 0, "total_chars": 0, "avg_length": 0}
        
        start_time = time.time()
        
        # Generate cache key for this batch
        batch_key = hashlib.md5(''.join(texts).encode()).hexdigest()
        
        if batch_key in self.text_stats_cache:
            logger.debug("Returning cached text analysis results")
            return self.text_stats_cache[batch_key]
        
        if self.cupy_available and len(texts) > 100:
            results = self._gpu_text_analysis(texts)
        else:
            results = self._cpu_text_analysis(texts)
        
        # Cache results
        self.text_stats_cache[batch_key] = results
        
        processing_time = time.time() - start_time
        logger.debug(f"Text analysis completed in {processing_time:.3f}s ({len(texts)} texts)")
        
        return results
    
    def _gpu_text_analysis(self, texts: List[str]) -> Dict[str, Any]:
        """GPU-accelerated text analysis using CuPy"""
        # Convert to GPU arrays
        text_lengths = cp.array([len(text) for text in texts])
        
        # Parallel computations
        total_chars = int(cp.sum(text_lengths))
        avg_length = float(cp.mean(text_lengths))
        max_length = int(cp.max(text_lengths))
        min_length = int(cp.min(text_lengths))
        std_length = float(cp.std(text_lengths))
        
        # Character frequency analysis
        char_counts = cp.zeros(256)  # ASCII characters
        for text in texts:
            for char in text:
                char_counts[ord(char) % 256] += 1
        
        # Most common characters
        top_chars_indices = cp.argsort(char_counts)[-10:][::-1]
        top_chars = [(int(idx), int(char_counts[idx])) for idx in top_chars_indices if char_counts[idx] > 0]
        
        return {
            "num_texts": len(texts),
            "total_chars": total_chars,
            "avg_length": avg_length,
            "max_length": max_length,
            "min_length": min_length,
            "std_length": std_length,
            "top_characters": top_chars,
            "processing_mode": "GPU"
        }
    
    def _cpu_text_analysis(self, texts: List[str]) -> Dict[str, Any]:
        """CPU fallback for text analysis"""
        text_lengths = [len(text) for text in texts]
        
        total_chars = sum(text_lengths)
        avg_length = total_chars / len(texts) if texts else 0
        max_length = max(text_lengths) if text_lengths else 0
        min_length = min(text_lengths) if text_lengths else 0
        
        # Standard deviation
        if len(text_lengths) > 1:
            variance = sum((x - avg_length) ** 2 for x in text_lengths) / len(text_lengths)
            std_length = variance ** 0.5
        else:
            std_length = 0
        
        # Character frequency analysis
        char_counts = {}
        for text in texts:
            for char in text:
                char_counts[char] = char_counts.get(char, 0) + 1
        
        # Top characters
        top_chars = sorted(char_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        top_chars = [(ord(char), count) for char, count in top_chars]
        
        return {
            "num_texts": len(texts),
            "total_chars": total_chars,
            "avg_length": avg_length,
            "max_length": max_length,
            "min_length": min_length,
            "std_length": std_length,
            "top_characters": top_chars,
            "processing_mode": "CPU"
        }
    
    def batch_pattern_search(self, texts: List[str], patterns: List[str]) -> Dict[str, List[int]]:
        """Batch pattern searching across texts"""
        results = {}
        
        for pattern in patterns:
            matching_indices = []
            pattern_lower = pattern.lower()
            
            for i, text in enumerate(texts):
                if pattern_lower in text.lower():
                    matching_indices.append(i)
            
            results[pattern] = matching_indices
        
        return results

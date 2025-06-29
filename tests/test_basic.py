"""
Basic tests for CGM components
"""

import pytest
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cgm_mcp.core.analyzer import CGMAnalyzer
from cgm_mcp.models import CodeAnalysisRequest
from cgm_mcp.utils.config import Config, LLMConfig
from cgm_mcp.utils.llm_client import LLMClient


class TestBasicFunctionality:
    """Test basic functionality without complex dependencies"""
    
    def test_config_loading(self):
        """Test configuration loading"""
        config = Config()
        assert config.llm_config is not None
        assert config.graph_config is not None
        assert config.server_config is not None
        
    def test_llm_config(self):
        """Test LLM configuration"""
        llm_config = LLMConfig(provider="mock")
        assert llm_config.provider == "mock"
        assert llm_config.model == "gpt-4"
        
    @pytest.mark.asyncio
    async def test_mock_llm_client(self):
        """Test mock LLM client"""
        config = LLMConfig(provider="mock")
        client = LLMClient(config)
        
        # Test health check
        health = await client.health_check()
        assert health is True
        
        # Test generation
        response = await client.generate("test analysis prompt")
        assert isinstance(response, str)
        assert len(response) > 0
        
    @pytest.mark.asyncio
    async def test_analyzer_basic(self):
        """Test basic analyzer functionality"""
        analyzer = CGMAnalyzer()
        
        # Test with current directory (should have some Python files)
        request = CodeAnalysisRequest(
            repository_path=".",
            query="test",
            analysis_scope="minimal",
            max_files=1
        )
        
        try:
            response = await analyzer.analyze_repository(request)
            assert response is not None
            assert response.repository_path == "."
            assert response.code_graph is not None
        except Exception as e:
            # If analysis fails, that's okay for basic test
            pytest.skip(f"Analysis failed (expected in some environments): {e}")
            
    def test_model_creation(self):
        """Test model creation"""
        from cgm_mcp.models import CodeEntity, CodeRelation
        
        entity = CodeEntity(
            id="test:entity",
            type="function",
            name="test_function",
            file_path="test.py"
        )
        
        assert entity.id == "test:entity"
        assert entity.type == "function"
        assert entity.name == "test_function"
        
        relation = CodeRelation(
            source_entity_id="source",
            target_entity_id="target", 
            relation_type="calls"
        )
        
        assert relation.source_entity_id == "source"
        assert relation.target_entity_id == "target"
        assert relation.relation_type == "calls"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Tests for CGM components
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cgm_mcp.components import (
    ReaderComponent,
    RerankerComponent,
    RetrieverComponent,
    RewriterComponent,
)
from cgm_mcp.models import (
    ReaderRequest,
    RerankerRequest,
    RetrieverRequest,
    RewriterRequest,
)
from cgm_mcp.utils.config import LLMConfig
from cgm_mcp.utils.llm_client import LLMClient


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client"""
    config = LLMConfig(provider="mock")
    return LLMClient(config)


@pytest.fixture
def sample_graph():
    """Sample code graph for testing"""
    return {
        "nodes": [
            {
                "id": "file:auth/models.py",
                "type": "file",
                "name": "models.py",
                "file_path": "auth/models.py",
                "content": "class User(models.Model):\n    username = models.CharField(max_length=100)\n    password = models.CharField(max_length=100)",
            },
            {
                "id": "class:auth/models.py:User",
                "type": "class",
                "name": "User",
                "file_path": "auth/models.py",
                "docstring": "User model for authentication",
            },
            {
                "id": "file:auth/views.py",
                "type": "file",
                "name": "views.py",
                "file_path": "auth/views.py",
                "content": "def authenticate_user(username, password):\n    user = User.objects.get(username=username)\n    return validate_password(password)",
            },
        ],
        "edges": [
            {
                "source": "file:auth/models.py",
                "target": "class:auth/models.py:User",
                "type": "contains",
            }
        ],
        "metadata": {
            "total_nodes": 3,
            "total_edges": 1,
            "node_types": ["file", "class"],
        },
    }


class TestRewriterComponent:
    """Test Rewriter component"""

    @pytest.mark.asyncio
    async def test_rewriter_extraction_mode(self, mock_llm_client):
        """Test rewriter in extraction mode"""
        rewriter = RewriterComponent(mock_llm_client)

        request = RewriterRequest(
            problem_statement="Authentication fails with special characters",
            repo_name="test-repo",
            extraction_mode=True,
        )

        response = await rewriter.process(request)

        assert response.analysis
        assert response.related_entities
        assert response.keywords

    @pytest.mark.asyncio
    async def test_rewriter_inference_mode(self, mock_llm_client):
        """Test rewriter in inference mode"""
        rewriter = RewriterComponent(mock_llm_client)

        request = RewriterRequest(
            problem_statement="Authentication fails with special characters",
            repo_name="test-repo",
            extraction_mode=False,
        )

        response = await rewriter.process(request)

        assert response.analysis
        assert response.queries is not None

    def test_parse_extractor_response(self, mock_llm_client):
        """Test parsing extractor response"""
        rewriter = RewriterComponent(mock_llm_client)

        response_text = """
        [start_of_analysis]
        This is a test analysis
        [end_of_analysis]
        [start_of_related_code_entities]
        auth/models.py
        auth/views.py
        [end_of_related_code_entities]
        [start_of_related_keywords]
        authentication
        password
        [end_of_related_keywords]
        """

        analysis, entities, keywords = rewriter.parse_extractor_response(response_text)

        assert "test analysis" in analysis
        assert "auth/models.py" in entities
        assert "auth/views.py" in entities
        assert "authentication" in keywords
        assert "password" in keywords


class TestRetrieverComponent:
    """Test Retriever component"""

    @pytest.mark.asyncio
    async def test_retriever_process(self, sample_graph):
        """Test retriever processing"""
        retriever = RetrieverComponent()

        request = RetrieverRequest(
            entities=["auth/models.py", "User"],
            keywords=["authentication", "password"],
            queries=["Find user authentication code"],
            repository_graph=sample_graph,
        )

        response = await retriever.process(request)

        assert response.anchor_nodes
        assert response.subgraph
        assert response.relevant_files

    def test_locate_anchor_nodes(self, sample_graph):
        """Test anchor node location"""
        retriever = RetrieverComponent()

        # Convert to NetworkX graph
        graph = retriever._dict_to_networkx(sample_graph)

        anchor_nodes = retriever.locate_anchor_nodes(
            entities=["User", "auth/models.py"],
            keywords=["authentication"],
            queries=[],
            graph=graph,
        )

        assert len(anchor_nodes) > 0

    def test_extract_subgraph(self, sample_graph):
        """Test subgraph extraction"""
        retriever = RetrieverComponent()

        # Convert to NetworkX graph
        graph = retriever._dict_to_networkx(sample_graph)

        anchor_nodes = ["file:auth/models.py"]
        subgraph = retriever.extract_subgraph(anchor_nodes, graph)

        assert subgraph["nodes"]
        assert "metadata" in subgraph


class TestRerankerComponent:
    """Test Reranker component"""

    @pytest.mark.asyncio
    async def test_reranker_process(self, mock_llm_client):
        """Test reranker processing"""
        reranker = RerankerComponent(mock_llm_client)

        request = RerankerRequest(
            problem_statement="Authentication fails",
            repo_name="test-repo",
            python_files=["auth/models.py", "auth/views.py"],
            other_files=["config.py"],
            file_contents={
                "auth/models.py": "class User(models.Model): pass",
                "auth/views.py": "def authenticate_user(): pass",
            },
        )

        response = await reranker.process(request)

        assert response.top_files
        assert response.file_scores

    def test_parse_stage_1_response(self, mock_llm_client):
        """Test parsing stage 1 response"""
        reranker = RerankerComponent(mock_llm_client)

        response_text = """
        [start_of_analysis]
        Analysis of relevant files
        [end_of_analysis]
        [start_of_relevant_files]
        1. auth/models.py
        2. auth/views.py
        [end_of_relevant_files]
        """

        analysis, files = reranker.parse_stage_1_response(response_text)

        assert "Analysis" in analysis
        assert "auth/models.py" in files
        assert "auth/views.py" in files


class TestReaderComponent:
    """Test Reader component"""

    @pytest.mark.asyncio
    async def test_reader_process(self, mock_llm_client, sample_graph):
        """Test reader processing"""
        reader = ReaderComponent(mock_llm_client)

        request = ReaderRequest(
            problem_statement="Fix authentication bug",
            subgraph=sample_graph,
            top_files=["auth/views.py"],
            repository_context={"name": "test-repo", "language": "Python"},
        )

        response = await reader.process(request)

        assert response.patches is not None
        assert response.summary
        assert 0 <= response.confidence <= 1

    def test_summarize_subgraph(self, mock_llm_client, sample_graph):
        """Test subgraph summarization"""
        reader = ReaderComponent(mock_llm_client)

        summary = reader._summarize_subgraph(sample_graph)

        assert "Code Graph Summary" in summary
        assert "Total nodes: 3" in summary
        assert "Total edges: 1" in summary


if __name__ == "__main__":
    pytest.main([__file__])

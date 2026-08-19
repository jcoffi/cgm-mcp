"""
Regression tests for reader hallucination fix.

Tests source loading, reader grounding, and output validation.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cgm_mcp.utils.source_loader import load_file_contents
from cgm_mcp.components.reader import ReaderComponent
from cgm_mcp.models import ReaderRequest, ReaderResponse


class TestSourceLoader:
    """Tests for source file loading utility."""

    def test_load_file_contents_basic(self, tmp_path):
        """Test loading a file from a repo directory."""
        (tmp_path / "hello.py").write_text("print('hello')\n")
        result = load_file_contents(str(tmp_path), ["hello.py"])
        assert "hello.py" in result
        assert "print('hello')" in result["hello.py"]

    def test_path_traversal_rejected(self, tmp_path):
        """Test that path traversal is blocked."""
        (tmp_path / "safe.py").write_text("safe")
        result = load_file_contents(str(tmp_path), ["../etc/passwd"])
        assert "../etc/passwd" not in result

    def test_symlink_rejected(self, tmp_path):
        """Test that symlinks are rejected."""
        target = tmp_path / "real.py"
        target.write_text("real content")
        link = tmp_path / "link.py"
        link.symlink_to(target)
        result = load_file_contents(str(tmp_path), ["link.py"])
        assert "link.py" not in result

    def test_aggregate_byte_limit(self, tmp_path):
        """Test that aggregate byte limit stops loading."""
        for i in range(5):
            (tmp_path / f"file{i}.py").write_text("x" * 200)
        result = load_file_contents(
            str(tmp_path),
            [f"file{i}.py" for i in range(5)],
            max_total_bytes=500,
        )
        # Should not load all 5 files (5*200=1000 > 500)
        assert len(result) < 5

    def test_file_count_limit(self, tmp_path):
        """Test that file count limit is enforced."""
        for i in range(10):
            (tmp_path / f"file{i}.py").write_text("content")
        result = load_file_contents(
            str(tmp_path),
            [f"file{i}.py" for i in range(10)],
            max_files=3,
        )
        assert len(result) <= 3

    def test_function_after_1000_chars_loaded(self, tmp_path):
        """Regression: a function beyond char 1000 must be present in loaded content."""
        # Create a file where target function starts well after char 1000
        padding = "# " + "x" * 998 + "\n"  # ~1000 chars
        target_fn = "\ndef _run_leak_gate(data):\n    SENTINEL_XYZ_123 = True\n    return SENTINEL_XYZ_123\n"
        content = padding + target_fn
        (tmp_path / "run_all_variants.py").write_text(content)

        result = load_file_contents(str(tmp_path), ["run_all_variants.py"])
        assert "run_all_variants.py" in result
        assert "SENTINEL_XYZ_123" in result["run_all_variants.py"]

    def test_nonexistent_repo_returns_empty(self):
        """Test that a non-existent repo path returns empty dict."""
        result = load_file_contents("/nonexistent/path", ["file.py"])
        assert result == {}


class TestReaderValidation:
    """Tests for reader output validation logic."""

    def test_summary_claims_changes_detection(self):
        """Test detection of summaries that claim changes were made."""
        from cgm_mcp.server import CGMServer
        from cgm_mcp.utils.config import Config

        config = Config()
        server = CGMServer(config)

        # Should detect change claims
        assert server._summary_claims_changes(
            "The patches implement a consistent gate-checking pattern"
        )
        assert server._summary_claims_changes(
            "_run_leak_gate now returns structured result"
        )
        assert server._summary_claims_changes(
            "score_fn has been updated to accept gate_result"
        )

        # Should NOT flag neutral summaries
        assert not server._summary_claims_changes(
            "Analysis found no actionable changes needed."
        )
        assert not server._summary_claims_changes("")
        assert not server._summary_claims_changes(
            "The code was reviewed and the function appears correct."
        )

    def test_reader_prompt_includes_source(self):
        """Test that source content appears in the reader prompt."""
        from cgm_mcp.utils.config import Config, LLMConfig

        config = LLMConfig(provider="mock")
        from cgm_mcp.utils.llm_client import LLMClient

        client = LLMClient(config)
        reader = ReaderComponent(client)

        file_contents = {"main.py": "def foo():\n    return 42\n"}
        prompt = reader.generate_patch_prompt(
            problem_statement="Fix foo",
            subgraph={"nodes": [], "edges": [], "metadata": {}},
            top_files=["main.py"],
            repository_context={"name": "test"},
            file_contents=file_contents,
        )
        assert "def foo():" in prompt
        assert "return 42" in prompt
        assert "--- FILE: main.py ---" in prompt

    def test_reader_prompt_no_source_warns(self):
        """Test that missing source produces warning in prompt."""
        from cgm_mcp.utils.config import LLMConfig
        from cgm_mcp.utils.llm_client import LLMClient

        client = LLMClient(LLMConfig(provider="mock"))
        reader = ReaderComponent(client)

        prompt = reader.generate_patch_prompt(
            problem_statement="Fix foo",
            subgraph={"nodes": [], "edges": [], "metadata": {}},
            top_files=["main.py"],
            repository_context={"name": "test"},
            file_contents={},
        )
        assert "No source code available" in prompt
        assert "MUST NOT claim" in prompt


class TestReaderHallucinationRegression:
    """End-to-end regression: empty patches + change-claiming summary must be rejected."""

    @pytest.mark.asyncio
    async def test_empty_patches_with_change_summary_rejected(self):
        """A reader response with no patches but claiming changes must not be 'completed'."""
        from cgm_mcp.server import CGMServer
        from cgm_mcp.utils.config import Config

        config = Config()
        server = CGMServer(config)

        # Simulate the scenario: mock the full pipeline
        hallucinating_response = (
            "[start_of_analysis]\nAnalysis done\n[end_of_analysis]\n"
            "[start_of_patches]\n[end_of_patches]\n"
            "[start_of_summary]\n"
            "The patches implement a consistent gate-checking pattern across all functions. "
            "_run_leak_gate now returns structured result.\n"
            "[end_of_summary]"
        )

        with patch.object(
            server.llm_client, "generate", new_callable=AsyncMock
        ) as mock_gen:
            # Rewriter mock
            mock_gen.side_effect = [
                # Rewriter response
                '{"analysis": "test", "related_entities": ["main.py"], "keywords": ["test"], "queries": []}',
                # Reranker response
                '{"scores": [{"file": "main.py", "score": 5, "analysis": "relevant"}]}',
                # Reader response (hallucinating)
                hallucinating_response,
            ]

            with tempfile.TemporaryDirectory() as tmp_dir:
                # Create a test file
                Path(tmp_dir, "main.py").write_text(
                    "# padding\n" * 200 + "def _run_leak_gate():\n    pass\n"
                )

                result = await server._process_issue(
                    {
                        "task_type": "bug_fixing",
                        "repository_name": "test_repo",
                        "issue_description": "Fix _run_leak_gate",
                        "repository_context": {"path": tmp_dir, "name": "test_repo"},
                    }
                )

                # The task should NOT be "completed" since patches are empty
                # but summary claims changes
                assert result.status != "completed" or (
                    result.reader_result
                    and "no applicable patches" in result.reader_result.summary.lower()
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

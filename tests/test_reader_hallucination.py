"""
Regression tests for reader hallucination fix.

Tests source loading, reader grounding, patch validation, and output consistency.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cgm_mcp.utils.source_loader import (
    load_file_contents,
    resolve_repo_path,
    validate_repo_path,
)
from cgm_mcp.components.reader import ReaderComponent
from cgm_mcp.models import CodePatch, ReaderResponse


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

    def test_hard_byte_limit_binary_read(self, tmp_path):
        """Regression: multibyte chars must not exceed configured byte limits."""
        # 400 'é' characters = 800 UTF-8 bytes
        content = "é" * 400
        (tmp_path / "multi.py").write_text(content, encoding="utf-8")

        result = load_file_contents(
            str(tmp_path),
            ["multi.py"],
            max_file_bytes=500,
            max_total_bytes=500,
        )
        assert "multi.py" in result
        # The raw bytes read must not exceed 500
        raw_bytes = result["multi.py"].encode("utf-8", errors="ignore")
        assert len(raw_bytes) <= 500

    def test_aggregate_byte_limit_hard(self, tmp_path):
        """Test that aggregate byte limit is never exceeded."""
        for i in range(5):
            (tmp_path / f"file{i}.py").write_text("x" * 200)
        result = load_file_contents(
            str(tmp_path),
            [f"file{i}.py" for i in range(5)],
            max_total_bytes=500,
        )
        total = sum(len(v.encode("utf-8")) for v in result.values())
        assert total <= 500

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

    def test_out_of_allowed_root_rejected(self, tmp_path):
        """Regression: repo path outside allowed_root must be rejected."""
        allowed = tmp_path / "allowed"
        allowed.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "secret.py").write_text("SECRET=123")

        result = validate_repo_path(str(outside), allowed_root=str(allowed))
        assert result is None

    def test_within_allowed_root_accepted(self, tmp_path):
        """Repo path inside allowed_root is accepted."""
        allowed = tmp_path / "allowed"
        repo = allowed / "myrepo"
        repo.mkdir(parents=True)

        result = validate_repo_path(str(repo), allowed_root=str(allowed))
        assert result is not None

    @pytest.mark.asyncio
    async def test_graph_builder_rejects_symlinked_source_file(self, tmp_path):
        """Graph construction must not follow source symlinks out of the repo."""
        from cgm_mcp.components.graph_builder import GraphBuilder

        repo = tmp_path / "repo"
        repo.mkdir()
        outside = tmp_path / "outside.py"
        outside.write_text("SECRET_SENTINEL = 'must not be read'\n")
        (repo / "linked.py").symlink_to(outside)

        graph = await GraphBuilder().build_graph("repo", {"path": str(repo)})

        assert all(node["id"] != "file:linked.py" for node in graph["nodes"])
        assert "SECRET_SENTINEL" not in str(graph)


class TestResolveRepoPath:
    """Tests for resolve_repo_path matching GraphBuilder logic."""

    def test_uses_context_path(self, tmp_path):
        """Should use repository_context['path'] when available."""
        result = resolve_repo_path("ignored", {"path": str(tmp_path)})
        assert result == os.path.realpath(str(tmp_path))

    def test_rejects_context_path_outside_root(self, tmp_path):
        """Should reject context path outside allowed_root."""
        allowed = tmp_path / "allowed"
        allowed.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()

        result = resolve_repo_path(
            "repo", {"path": str(outside)}, allowed_root=str(allowed)
        )
        assert result is None

    def test_default_allowed_root_is_current_directory(self):
        """Repository access is confined by default, not opt-in."""
        from cgm_mcp.utils.config import Config

        assert Config().server_config.allowed_root == os.getcwd()


class TestReaderValidation:
    """Tests for reader output validation logic."""

    def test_reader_prompt_includes_source(self):
        """Test that source content appears in the reader prompt."""
        from cgm_mcp.utils.config import LLMConfig
        from cgm_mcp.utils.llm_client import LLMClient

        client = LLMClient(LLMConfig(provider="mock"))
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


class TestPatchValidation:
    """Tests for patch validation in server."""

    def test_patch_with_unknown_file_rejected(self):
        """Patches targeting files not in loaded contents are rejected."""
        from cgm_mcp.server import CGMServer
        from cgm_mcp.utils.config import Config

        server = CGMServer(Config())

        reader_result = ReaderResponse(
            patches=[
                CodePatch(
                    file_path="nonexistent.py",
                    original_code="old code",
                    modified_code="new code",
                    line_start=1,
                    line_end=5,
                    explanation="fix",
                )
            ],
            summary="Fixed the bug",
            confidence=0.8,
        )
        file_contents = {"main.py": "def foo():\n    pass\n"}

        status, error = server._validate_reader_output(
            "test-id", "bug_fixing", reader_result, file_contents
        )
        assert status == "completed_no_patches"
        assert reader_result.patches == []

    def test_patch_with_wrong_original_code_rejected(self):
        """Patches whose original_code doesn't exist in source are rejected."""
        from cgm_mcp.server import CGMServer
        from cgm_mcp.utils.config import Config

        server = CGMServer(Config())

        reader_result = ReaderResponse(
            patches=[
                CodePatch(
                    file_path="main.py",
                    original_code="this does not exist in source",
                    modified_code="new code",
                    line_start=1,
                    line_end=5,
                    explanation="fix",
                )
            ],
            summary="Fixed the bug",
            confidence=0.8,
        )
        file_contents = {"main.py": "def foo():\n    pass\n"}

        status, error = server._validate_reader_output(
            "test-id", "bug_fixing", reader_result, file_contents
        )
        assert status == "completed_no_patches"
        assert reader_result.patches == []

    def test_valid_patch_accepted(self):
        """Patches with correct file and matching original_code are accepted."""
        from cgm_mcp.server import CGMServer
        from cgm_mcp.utils.config import Config

        server = CGMServer(Config())

        reader_result = ReaderResponse(
            patches=[
                CodePatch(
                    file_path="main.py",
                    original_code="def foo():\n    pass",
                    modified_code="def foo():\n    return 42",
                    line_start=1,
                    line_end=2,
                    explanation="fix return value",
                )
            ],
            summary="Fixed foo",
            confidence=0.8,
        )
        file_contents = {"main.py": "def foo():\n    pass\n"}

        status, error = server._validate_reader_output(
            "test-id", "bug_fixing", reader_result, file_contents
        )
        assert status == "completed"
        assert len(reader_result.patches) == 1

    def test_patch_original_must_match_claimed_line_range(self):
        """A snippet elsewhere in the file cannot validate a wrong range."""
        from cgm_mcp.server import CGMServer
        from cgm_mcp.utils.config import Config

        reader_result = ReaderResponse(
            patches=[
                CodePatch(
                    file_path="main.py",
                    original_code="def foo():\n    pass",
                    modified_code="def foo():\n    return 42",
                    line_start=4,
                    line_end=5,
                    explanation="wrong range",
                )
            ],
            summary="Fixed foo",
            confidence=0.8,
        )
        source = "def foo():\n    pass\n\ndef bar():\n    pass\n"

        status, _ = CGMServer(Config())._validate_reader_output(
            "test-id", "bug_fixing", reader_result, {"main.py": source}
        )

        assert status == "completed_no_patches"
        assert reader_result.patches == []

    def test_mixed_valid_and_invalid_patches_fail_closed(self):
        """A hallucinated patch invalidates the response and its summary."""
        from cgm_mcp.server import CGMServer
        from cgm_mcp.utils.config import Config

        reader_result = ReaderResponse(
            patches=[
                CodePatch(
                    file_path="main.py",
                    original_code="def foo():\n    pass",
                    modified_code="def foo():\n    return 42",
                    line_start=1,
                    line_end=2,
                    explanation="valid",
                ),
                CodePatch(
                    file_path="invented.py",
                    original_code="invented",
                    modified_code="also invented",
                    line_start=1,
                    line_end=1,
                    explanation="hallucinated",
                ),
            ],
            summary="Fixed main.py and invented.py",
            confidence=0.9,
        )

        status, _ = CGMServer(Config())._validate_reader_output(
            "test-id",
            "bug_fixing",
            reader_result,
            {"main.py": "def foo():\n    pass\n"},
        )

        assert status == "completed_no_patches"
        assert reader_result.patches == []
        assert "could not be validated" in reader_result.summary.lower()

    def test_zero_patches_bug_fixing_always_no_patches(self):
        """Bug fixing task with zero patches is always completed_no_patches."""
        from cgm_mcp.server import CGMServer
        from cgm_mcp.utils.config import Config

        server = CGMServer(Config())

        # Even with source loaded, zero patches for bug_fixing => not completed
        reader_result = ReaderResponse(
            patches=[],
            summary="Implemented the fix successfully",  # hallucinating
            confidence=0.6,
        )
        file_contents = {"main.py": "def foo():\n    pass\n"}

        status, error = server._validate_reader_output(
            "test-id", "bug_fixing", reader_result, file_contents
        )
        assert status == "completed_no_patches"
        assert (
            "no applicable patches" in reader_result.summary.lower()
            or "no concrete code changes" in reader_result.summary.lower()
        )
        assert reader_result.confidence <= 0.3

    def test_zero_patches_code_analysis_is_completed(self):
        """Code analysis task with zero patches can still be completed."""
        from cgm_mcp.server import CGMServer
        from cgm_mcp.utils.config import Config

        server = CGMServer(Config())

        reader_result = ReaderResponse(
            patches=[],
            summary="The code looks correct.",
            confidence=0.6,
        )
        file_contents = {"main.py": "def foo():\n    pass\n"}

        status, error = server._validate_reader_output(
            "test-id", "code_analysis", reader_result, file_contents
        )
        assert status == "completed"

    def test_patch_with_empty_original_code_rejected(self):
        """Patches with empty original_code are rejected."""
        from cgm_mcp.server import CGMServer
        from cgm_mcp.utils.config import Config

        server = CGMServer(Config())

        reader_result = ReaderResponse(
            patches=[
                CodePatch(
                    file_path="main.py",
                    original_code="",
                    modified_code="new code",
                    line_start=1,
                    line_end=2,
                    explanation="fix",
                )
            ],
            summary="Fixed it",
            confidence=0.8,
        )
        file_contents = {"main.py": "def foo():\n    pass\n"}

        status, error = server._validate_reader_output(
            "test-id", "bug_fixing", reader_result, file_contents
        )
        assert status == "completed_no_patches"
        assert reader_result.patches == []

    def test_patch_with_invalid_line_range_rejected(self):
        """Patches with out-of-bounds line ranges are rejected."""
        from cgm_mcp.server import CGMServer
        from cgm_mcp.utils.config import Config

        server = CGMServer(Config())

        reader_result = ReaderResponse(
            patches=[
                CodePatch(
                    file_path="main.py",
                    original_code="def foo():\n    pass",
                    modified_code="def foo():\n    return 1",
                    line_start=-10,
                    line_end=9999,
                    explanation="fix",
                )
            ],
            summary="Fixed it",
            confidence=0.8,
        )
        file_contents = {"main.py": "def foo():\n    pass\n"}

        status, error = server._validate_reader_output(
            "test-id", "bug_fixing", reader_result, file_contents
        )
        assert status == "completed_no_patches"
        assert reader_result.patches == []

    def test_patch_with_empty_modified_code_rejected(self):
        """Patches with empty modified_code are rejected."""
        from cgm_mcp.server import CGMServer
        from cgm_mcp.utils.config import Config

        server = CGMServer(Config())

        reader_result = ReaderResponse(
            patches=[
                CodePatch(
                    file_path="main.py",
                    original_code="def foo():\n    pass",
                    modified_code="",
                    line_start=1,
                    line_end=2,
                    explanation="fix",
                )
            ],
            summary="Fixed it",
            confidence=0.8,
        )
        file_contents = {"main.py": "def foo():\n    pass\n"}

        status, error = server._validate_reader_output(
            "test-id", "bug_fixing", reader_result, file_contents
        )
        assert status == "completed_no_patches"
        assert reader_result.patches == []


class TestPatchParserIndentation:
    """Tests for patch parser preserving code indentation."""

    def test_indented_code_preserved_in_parsing(self):
        """Verify that _parse_single_patch preserves Python indentation."""
        from cgm_mcp.utils.config import LLMConfig
        from cgm_mcp.utils.llm_client import LLMClient

        client = LLMClient(LLMConfig(provider="mock"))
        reader = ReaderComponent(client)

        patch_block = (
            "\nFile: main.py\n"
            "Description: Fix return value\n"
            "Line Range: 1-3\n"
            "Original Code:\n"
            "```\n"
            "def foo():\n"
            "    if True:\n"
            "        pass\n"
            "```\n"
            "Modified Code:\n"
            "```\n"
            "def foo():\n"
            "    if True:\n"
            "        return 42\n"
            "```\n"
            "Explanation: Fixed return\n"
        )

        patch = reader._parse_single_patch(patch_block)
        assert patch is not None
        assert "    if True:" in patch.original_code
        assert "        pass" in patch.original_code
        assert "    if True:" in patch.modified_code
        assert "        return 42" in patch.modified_code

    def test_indented_patch_passes_validation(self):
        """E2E: indented patch that matches source passes validation."""
        from cgm_mcp.server import CGMServer
        from cgm_mcp.utils.config import Config

        server = CGMServer(Config())
        source = "def foo():\n    if True:\n        pass\n"

        reader_result = ReaderResponse(
            patches=[
                CodePatch(
                    file_path="main.py",
                    original_code="def foo():\n    if True:\n        pass",
                    modified_code="def foo():\n    if True:\n        return 42",
                    line_start=1,
                    line_end=3,
                    explanation="fix return value",
                )
            ],
            summary="Fixed foo",
            confidence=0.8,
        )
        file_contents = {"main.py": source}

        status, error = server._validate_reader_output(
            "test-id", "bug_fixing", reader_result, file_contents
        )
        assert status == "completed"
        assert len(reader_result.patches) == 1

    def test_missing_line_range_is_rejected(self):
        """A parser default must not make a missing range look valid."""
        from cgm_mcp.server import CGMServer
        from cgm_mcp.utils.config import Config, LLMConfig
        from cgm_mcp.utils.llm_client import LLMClient

        reader = ReaderComponent(LLMClient(LLMConfig(provider="mock")))
        patch = reader._parse_single_patch(
            "\nFile: main.py\n"
            "Original Code:\n```\ndef foo():\n```\n"
            "Modified Code:\n```\ndef foo(): return 42\n```\n"
            "Explanation: fix\n"
        )

        assert patch is not None
        status, _ = CGMServer(Config())._validate_reader_output(
            "test-id",
            "bug_fixing",
            ReaderResponse(patches=[patch], summary="Fixed", confidence=0.8),
            {"main.py": "def foo():\n"},
        )
        assert status == "completed_no_patches"


class TestRepoPathValidationOrder:
    """Tests that repo path validation happens before graph traversal."""

    @pytest.mark.asyncio
    async def test_out_of_root_rejected_before_graph(self):
        """Out-of-root repo fails before any file I/O or graph construction."""
        from cgm_mcp.server import CGMServer
        from cgm_mcp.utils.config import Config, ServerConfig

        config = Config()
        with tempfile.TemporaryDirectory() as allowed_dir:
            with tempfile.TemporaryDirectory() as outside_dir:
                # Create a file in the outside dir to prove it's never read
                Path(outside_dir, "secret.py").write_text("SECRET=True")
                config.server_config.allowed_root = allowed_dir

                server = CGMServer(config)
                result = await server._process_issue(
                    {
                        "task_type": "bug_fixing",
                        "repository_name": "evil_repo",
                        "issue_description": "Steal secrets",
                        "repository_context": {
                            "path": outside_dir,
                            "name": "evil_repo",
                        },
                    }
                )

                # Must fail before reaching rewriter/graph
                assert result.status == "insufficient_context"
                assert result.rewriter_result is None
                assert result.retriever_result is None


class TestReaderHallucinationRegression:
    """End-to-end regression: empty patches + change-claiming summary must be rejected."""

    @pytest.mark.asyncio
    async def test_empty_patches_with_hallucinating_summary(self):
        """
        Full pipeline: rewriter produces valid markers, reranker scores files,
        reader produces empty patches with a hallucinating summary.
        The result must NOT be 'completed'.
        """
        from cgm_mcp.server import CGMServer
        from cgm_mcp.utils.config import Config

        config = Config()
        server = CGMServer(config)

        # Valid rewriter response with proper markers
        rewriter_response = (
            "[start_of_analysis]\n"
            "The issue involves _run_leak_gate in main.py\n"
            "[end_of_analysis]\n"
            "[start_of_related_code_entities]\n"
            "main.py\n"
            "def _run_leak_gate()\n"
            "[end_of_related_code_entities]\n"
            "[start_of_related_keywords]\n"
            "leak_gate\n"
            "metrics\n"
            "blocking\n"
            "[end_of_related_keywords]"
        )

        # Reranker Stage 1 response (uses markers, not JSON)
        reranker_stage1_response = (
            "[start_of_analysis]\n"
            "main.py contains _run_leak_gate\n"
            "[end_of_analysis]\n"
            "[start_of_relevant_files]\n"
            "1. main.py\n"
            "[end_of_relevant_files]"
        )

        # Reranker Stage 2 response for main.py
        reranker_stage2_response = (
            "[start_of_analysis]\n"
            "Contains the target function\n"
            "[end_of_analysis]\n"
            "[start_of_score]\n"
            "Score 5\n"
            "[end_of_score]"
        )

        # Hallucinating reader response: empty patches but claims changes
        reader_response = (
            "[start_of_analysis]\n"
            "Analyzed the _run_leak_gate function.\n"
            "[end_of_analysis]\n"
            "[start_of_patches]\n"
            "[end_of_patches]\n"
            "[start_of_summary]\n"
            "The patches implement a consistent gate-checking pattern. "
            "_run_leak_gate now returns structured result.\n"
            "[end_of_summary]"
        )

        call_count = [0]
        responses = [
            rewriter_response,
            reranker_stage1_response,
            reranker_stage2_response,
            reader_response,
        ]

        async def mock_generate(prompt):
            idx = call_count[0]
            call_count[0] += 1
            return responses[idx]

        with patch.object(server.llm_client, "generate", side_effect=mock_generate):
            with tempfile.TemporaryDirectory() as tmp_dir:
                server.config.server_config.allowed_root = tmp_dir
                # Create test file with function after 1000 chars
                padding = "# padding line\n" * 100  # >1000 chars
                code = "def _run_leak_gate(data):\n    return {'blocked': True}\n"
                Path(tmp_dir, "main.py").write_text(padding + code)

                result = await server._process_issue(
                    {
                        "task_type": "bug_fixing",
                        "repository_name": "test_repo",
                        "issue_description": "Fix _run_leak_gate",
                        "repository_context": {"path": tmp_dir, "name": "test_repo"},
                    }
                )

                # Assert all 4 LLM calls were made (rewriter, reranker s1, reranker s2, reader)
                assert call_count[0] == 4

                # Must NOT be "completed" — should be "completed_no_patches"
                assert result.status == "completed_no_patches"

                # Summary must be sanitized
                assert (
                    "no applicable patches" in result.reader_result.summary.lower()
                    or "no concrete code changes"
                    in result.reader_result.summary.lower()
                )

                # Confidence must be capped
                assert result.reader_result.confidence <= 0.3

                # Persisted task matches
                task = server.tasks[result.task_id]
                assert task.status == result.status
                assert task.reader_result.summary == result.reader_result.summary

    @pytest.mark.asyncio
    async def test_invalid_patch_original_code_rejected_e2e(self):
        """
        Full pipeline: reader produces a patch with wrong original_code.
        The result must fail validation.
        """
        from cgm_mcp.server import CGMServer
        from cgm_mcp.utils.config import Config

        config = Config()
        server = CGMServer(config)

        rewriter_response = (
            "[start_of_analysis]\nAnalysis\n[end_of_analysis]\n"
            "[start_of_related_code_entities]\nmain.py\n[end_of_related_code_entities]\n"
            "[start_of_related_keywords]\nfoo\n[end_of_related_keywords]"
        )

        reranker_stage1_response = (
            "[start_of_analysis]\nrelevant\n[end_of_analysis]\n"
            "[start_of_relevant_files]\n1. main.py\n[end_of_relevant_files]"
        )

        reranker_stage2_response = (
            "[start_of_analysis]\nrelevant\n[end_of_analysis]\n"
            "[start_of_score]\nScore 5\n[end_of_score]"
        )

        # Reader invents original code that doesn't exist
        reader_response = (
            "[start_of_analysis]\nFound the issue\n[end_of_analysis]\n"
            "[start_of_patches]\n"
            "PATCH 1:\n"
            "File: main.py\n"
            "Description: Fix the bug\n"
            "Line Range: 1-5\n"
            "Original Code:\n```\ndef invented_function():\n    pass\n```\n"
            "Modified Code:\n```\ndef invented_function():\n    return True\n```\n"
            "Explanation: Fixed it\n"
            "[end_of_patches]\n"
            "[start_of_summary]\nFixed the bug\n[end_of_summary]"
        )

        call_count = [0]
        responses = [
            rewriter_response,
            reranker_stage1_response,
            reranker_stage2_response,
            reader_response,
        ]

        async def mock_generate(prompt):
            idx = call_count[0]
            call_count[0] += 1
            return responses[idx]

        with patch.object(server.llm_client, "generate", side_effect=mock_generate):
            with tempfile.TemporaryDirectory() as tmp_dir:
                server.config.server_config.allowed_root = tmp_dir
                Path(tmp_dir, "main.py").write_text("def real_function():\n    pass\n")

                result = await server._process_issue(
                    {
                        "task_type": "bug_fixing",
                        "repository_name": "test_repo",
                        "issue_description": "Fix the bug",
                        "repository_context": {"path": tmp_dir, "name": "test_repo"},
                    }
                )

                assert call_count[0] == 4
                assert result.status == "completed_no_patches"
                assert result.reader_result.patches == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

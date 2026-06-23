"""Tests for mcp/server.py — tool functions, _format, _ensure_docker_db, _lifespan."""

import asyncio
import subprocess
from unittest.mock import MagicMock, patch

import linguaalayam.mcp.server as server


class TestEnsureDockerDb:
    """_ensure_docker_db Docker interaction and error handling."""

    def test_starts_container_on_success(self):
        """Should sleep after a successful docker start."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        with (
            patch("linguaalayam.mcp.server.subprocess.run", return_value=mock_result),
            patch("linguaalayam.mcp.server.time.sleep") as mock_sleep,
        ):
            server._ensure_docker_db()
        mock_sleep.assert_called_once_with(2)

    def test_no_sleep_on_nonzero_returncode(self):
        """Should not sleep when docker start fails."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        with (
            patch("linguaalayam.mcp.server.subprocess.run", return_value=mock_result),
            patch("linguaalayam.mcp.server.time.sleep") as mock_sleep,
        ):
            server._ensure_docker_db()
        mock_sleep.assert_not_called()

    def test_docker_not_found_does_not_raise(self):
        """FileNotFoundError (Docker absent) should be silently swallowed."""
        with patch("linguaalayam.mcp.server.subprocess.run", side_effect=FileNotFoundError):
            server._ensure_docker_db()  # should not raise

    def test_timeout_does_not_raise(self):
        """TimeoutExpired should be silently swallowed."""
        with patch(
            "linguaalayam.mcp.server.subprocess.run",
            side_effect=subprocess.TimeoutExpired("docker", 10),
        ):
            server._ensure_docker_db()  # should not raise

    def test_respects_db_container_env(self):
        """DB_CONTAINER env var should override the default container name."""
        captured = []
        with (
            patch.dict("os.environ", {"DB_CONTAINER": "custom-pg"}),
            patch("linguaalayam.mcp.server.subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=1)
            mock_run.side_effect = lambda cmd, **kw: captured.append(cmd) or MagicMock(returncode=1)
            server._ensure_docker_db()
        assert captured[0][-1] == "custom-pg"


class TestInitTools:
    """_init_tools DictionaryTools construction."""

    def test_returns_dictionary_tools(self):
        """_init_tools should return a DictionaryTools instance."""
        from linguaalayam.rag.tools import DictionaryTools

        with (
            patch("linguaalayam.mcp.server.build_engine"),
            patch("linguaalayam.mcp.server.build_session_factory"),
            patch("linguaalayam.mcp.server.EmbeddingService"),
        ):
            tools = server._init_tools()
        assert isinstance(tools, DictionaryTools)


class TestLifespan:
    """_lifespan async context manager initialisation."""

    def test_initializes_tools(self):
        """_lifespan should assign a DictionaryTools instance to server._tools."""
        mock_tools = MagicMock()

        async def _run():
            with (
                patch("linguaalayam.mcp.server._ensure_docker_db"),
                patch("linguaalayam.mcp.server._init_tools", return_value=mock_tools),
            ):
                async with server._lifespan(MagicMock()):
                    assert server._tools is mock_tools

        asyncio.run(_run())


class TestFormat:
    """_format result formatting."""

    def test_empty_results(self):
        """Should return a 'No … results' message for an empty list."""
        result = server._format([], "run", "exact")
        assert "No exact results" in result
        assert "run" in result

    def test_single_result(self):
        """Should include headword, source, and embed_text for one result."""
        results = [
            {
                "headword": "run",
                "source": "olam_enml",
                "match_type": "exact",
                "score": 1.0,
                "embed_text": "word: run\n  [v] ഓടുക",
            }
        ]
        result = server._format(results, "run", "exact")
        assert "1 exact result" in result
        assert "run" in result
        assert "olam_enml" in result

    def test_multiple_results_counted(self):
        """Should report the correct result count."""
        results = [
            {
                "headword": "run",
                "source": "s",
                "match_type": "fuzzy",
                "score": 0.8,
                "embed_text": "x",
            },
            {
                "headword": "ran",
                "source": "s",
                "match_type": "fuzzy",
                "score": 0.7,
                "embed_text": "y",
            },
        ]
        result = server._format(results, "run", "fuzzy")
        assert "2 fuzzy result" in result


class TestResourceHandler:
    """get_entry MCP resource handler."""

    def setup_method(self):
        """Save original _tools so teardown can restore it."""
        self._orig_tools = server._tools

    def teardown_method(self):
        """Restore original _tools after each test."""
        server._tools = self._orig_tools

    def test_get_entry_returns_formatted_results(self):
        """get_entry should format exact lookup results for the given headword."""
        mock_tools = MagicMock()
        mock_tools.exact_lookup.return_value = [
            {
                "headword": "run",
                "source": "olam_enml",
                "match_type": "exact",
                "score": 1.0,
                "embed_text": "word: run\n  [v] ഓടുക",
            }
        ]
        server._tools = mock_tools
        result = server.get_entry("run")
        assert "run" in result
        assert "ഓടുക" in result

    def test_get_entry_no_results(self):
        """get_entry should return a 'No exact results' message on miss."""
        mock_tools = MagicMock()
        mock_tools.exact_lookup.return_value = []
        server._tools = mock_tools
        result = server.get_entry("xyzzy")
        assert "No exact results" in result

    def test_get_entry_calls_exact_lookup(self):
        """get_entry should call exact_lookup with the headword."""
        mock_tools = MagicMock()
        mock_tools.exact_lookup.return_value = []
        server._tools = mock_tools
        server.get_entry("water")
        mock_tools.exact_lookup.assert_called_once_with("water")


class TestToolFunctions:
    """MCP tool functions — exact_lookup, fuzzy_lookup, semantic_lookup."""

    def setup_method(self):
        """Save original _tools so teardown can restore it."""
        self._orig_tools = server._tools

    def teardown_method(self):
        """Restore original _tools after each test."""
        server._tools = self._orig_tools

    def test_exact_lookup_no_results(self):
        """exact_lookup should return a 'No exact results' message on miss."""
        mock_tools = MagicMock()
        mock_tools.exact_lookup.return_value = []
        server._tools = mock_tools
        result = server.exact_lookup("xyzzy")
        assert "No exact results" in result

    def test_exact_lookup_with_results(self):
        """exact_lookup should include the headword in the formatted output."""
        mock_tools = MagicMock()
        mock_tools.exact_lookup.return_value = [
            {
                "headword": "run",
                "source": "s",
                "match_type": "exact",
                "score": 1.0,
                "embed_text": "x",
            }
        ]
        server._tools = mock_tools
        result = server.exact_lookup("run")
        assert "run" in result

    def test_exact_lookup_passes_source(self):
        """Source parameter should be forwarded to DictionaryTools.exact_lookup."""
        mock_tools = MagicMock()
        mock_tools.exact_lookup.return_value = []
        server._tools = mock_tools
        server.exact_lookup("run", source="olam_enml")
        mock_tools.exact_lookup.assert_called_once_with("run", source="olam_enml")

    def test_fuzzy_lookup_no_results(self):
        """fuzzy_lookup should return a 'No fuzzy results' message on miss."""
        mock_tools = MagicMock()
        mock_tools.fuzzy_lookup.return_value = []
        server._tools = mock_tools
        result = server.fuzzy_lookup("runing")
        assert "No fuzzy results" in result

    def test_fuzzy_lookup_passes_params(self):
        """threshold, top_k, and source should be forwarded correctly."""
        mock_tools = MagicMock()
        mock_tools.fuzzy_lookup.return_value = []
        server._tools = mock_tools
        server.fuzzy_lookup("run", threshold=0.5, top_k=3, source="olam_enml")
        mock_tools.fuzzy_lookup.assert_called_once_with(
            "run", source="olam_enml", threshold=0.5, top_k=3
        )

    def test_semantic_lookup_no_results(self):
        """semantic_lookup should return a 'No semantic results' message on miss."""
        mock_tools = MagicMock()
        mock_tools.semantic_lookup.return_value = []
        server._tools = mock_tools
        result = server.semantic_lookup("to move quickly on foot")
        assert "No semantic results" in result

    def test_semantic_lookup_passes_params(self):
        """top_k and source should be forwarded to DictionaryTools.semantic_lookup."""
        mock_tools = MagicMock()
        mock_tools.semantic_lookup.return_value = []
        server._tools = mock_tools
        server.semantic_lookup("query", top_k=3, source="olam_enml")
        mock_tools.semantic_lookup.assert_called_once_with("query", top_k=3, source="olam_enml")

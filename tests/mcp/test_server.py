"""Tests for mcp/server.py — tool functions, _format, _ensure_docker_db, _lifespan."""

import asyncio
import subprocess
from unittest.mock import MagicMock, patch


import linguaalayam.mcp.server as server


class TestEnsureDockerDb:
    def test_starts_container_on_success(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        with (
            patch("linguaalayam.mcp.server.subprocess.run", return_value=mock_result),
            patch("linguaalayam.mcp.server.time.sleep") as mock_sleep,
        ):
            server._ensure_docker_db()
        mock_sleep.assert_called_once_with(2)

    def test_no_sleep_on_nonzero_returncode(self):
        mock_result = MagicMock()
        mock_result.returncode = 1
        with (
            patch("linguaalayam.mcp.server.subprocess.run", return_value=mock_result),
            patch("linguaalayam.mcp.server.time.sleep") as mock_sleep,
        ):
            server._ensure_docker_db()
        mock_sleep.assert_not_called()

    def test_docker_not_found_does_not_raise(self):
        with patch("linguaalayam.mcp.server.subprocess.run", side_effect=FileNotFoundError):
            server._ensure_docker_db()  # should not raise

    def test_timeout_does_not_raise(self):
        with patch(
            "linguaalayam.mcp.server.subprocess.run",
            side_effect=subprocess.TimeoutExpired("docker", 10),
        ):
            server._ensure_docker_db()  # should not raise

    def test_respects_db_container_env(self):
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
    def test_returns_dictionary_tools(self):
        from linguaalayam.rag.tools import DictionaryTools

        with (
            patch("linguaalayam.mcp.server.build_engine"),
            patch("linguaalayam.mcp.server.build_session_factory"),
            patch("linguaalayam.mcp.server.EmbeddingService"),
        ):
            tools = server._init_tools()
        assert isinstance(tools, DictionaryTools)


class TestLifespan:
    def test_initializes_tools(self):
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
    def test_empty_results(self):
        result = server._format([], "run", "exact")
        assert "No exact results" in result
        assert "run" in result

    def test_single_result(self):
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
    def setup_method(self):
        self._orig_tools = server._tools

    def teardown_method(self):
        server._tools = self._orig_tools

    def test_get_entry_returns_formatted_results(self):
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
        mock_tools = MagicMock()
        mock_tools.exact_lookup.return_value = []
        server._tools = mock_tools
        result = server.get_entry("xyzzy")
        assert "No exact results" in result

    def test_get_entry_calls_exact_lookup(self):
        mock_tools = MagicMock()
        mock_tools.exact_lookup.return_value = []
        server._tools = mock_tools
        server.get_entry("water")
        mock_tools.exact_lookup.assert_called_once_with("water")


class TestToolFunctions:
    def setup_method(self):
        self._orig_tools = server._tools

    def teardown_method(self):
        server._tools = self._orig_tools

    def test_exact_lookup_no_results(self):
        mock_tools = MagicMock()
        mock_tools.exact_lookup.return_value = []
        server._tools = mock_tools
        result = server.exact_lookup("xyzzy")
        assert "No exact results" in result

    def test_exact_lookup_with_results(self):
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
        mock_tools = MagicMock()
        mock_tools.exact_lookup.return_value = []
        server._tools = mock_tools
        server.exact_lookup("run", source="olam_enml")
        mock_tools.exact_lookup.assert_called_once_with("run", source="olam_enml")

    def test_fuzzy_lookup_no_results(self):
        mock_tools = MagicMock()
        mock_tools.fuzzy_lookup.return_value = []
        server._tools = mock_tools
        result = server.fuzzy_lookup("runing")
        assert "No fuzzy results" in result

    def test_fuzzy_lookup_passes_params(self):
        mock_tools = MagicMock()
        mock_tools.fuzzy_lookup.return_value = []
        server._tools = mock_tools
        server.fuzzy_lookup("run", threshold=0.5, top_k=3, source="olam_enml")
        mock_tools.fuzzy_lookup.assert_called_once_with(
            "run", source="olam_enml", threshold=0.5, top_k=3
        )

    def test_semantic_lookup_no_results(self):
        mock_tools = MagicMock()
        mock_tools.semantic_lookup.return_value = []
        server._tools = mock_tools
        result = server.semantic_lookup("to move quickly on foot")
        assert "No semantic results" in result

    def test_semantic_lookup_passes_params(self):
        mock_tools = MagicMock()
        mock_tools.semantic_lookup.return_value = []
        server._tools = mock_tools
        server.semantic_lookup("query", top_k=3, source="olam_enml")
        mock_tools.semantic_lookup.assert_called_once_with("query", top_k=3, source="olam_enml")

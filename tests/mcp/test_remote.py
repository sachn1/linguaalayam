"""Tests for mcp/remote.py's tool functions and per-call usage logging."""

from unittest.mock import MagicMock, patch

from starlette.requests import Request

import linguaalayam.mcp.remote as remote


def _request() -> Request:
    """Build a minimal real Starlette Request."""
    scope = {"type": "http", "headers": [], "client": ("203.0.113.1", 12345)}
    return Request(scope)


class TestLogToolCall:
    """_log_tool_call's best-effort logging, never breaking the tool call."""

    def test_logs_when_a_real_request_is_present(self):
        ctx = MagicMock()
        ctx.request_context.request = _request()
        with patch("linguaalayam.mcp.remote.log_feature_event") as mock_log:
            remote._log_tool_call(ctx, "exact_lookup", "run")
        mock_log.assert_called_once_with(
            "mcp_exact_lookup", ctx.request_context.request, query="run"
        )

    def test_skips_logging_when_no_request_context(self):
        ctx = MagicMock()
        ctx.request_context = None
        with patch("linguaalayam.mcp.remote.log_feature_event") as mock_log:
            remote._log_tool_call(ctx, "exact_lookup", "run")  # should not raise
        mock_log.assert_not_called()

    def test_skips_logging_when_request_is_not_a_starlette_request(self):
        """Stdio/non-HTTP transports expose something other than a real Request."""
        ctx = MagicMock()
        ctx.request_context.request = object()
        with patch("linguaalayam.mcp.remote.log_feature_event") as mock_log:
            remote._log_tool_call(ctx, "exact_lookup", "run")
        mock_log.assert_not_called()

    def test_accessing_request_context_raising_does_not_propagate(self):
        """ctx.request_context can raise (not return None) outside an active request."""
        ctx = MagicMock()
        type(ctx).request_context = property(lambda self: (_ for _ in ()).throw(RuntimeError))
        remote._log_tool_call(ctx, "exact_lookup", "run")  # should not raise

    def test_logging_failure_does_not_propagate(self):
        ctx = MagicMock()
        ctx.request_context.request = _request()
        with patch(
            "linguaalayam.mcp.remote.log_feature_event", side_effect=RuntimeError("db down")
        ):
            remote._log_tool_call(ctx, "exact_lookup", "run")  # should not raise


class TestTools:
    """Tool functions delegate to get_tools() and format the result."""

    def test_get_entry_calls_exact_lookup(self):
        mock_tools = MagicMock()
        mock_tools.exact_lookup.return_value = []
        with patch("linguaalayam.mcp.remote.get_tools", return_value=mock_tools):
            remote.get_entry("run", ctx=MagicMock())
        mock_tools.exact_lookup.assert_called_once_with("run")

    def test_exact_lookup_passes_source(self):
        mock_tools = MagicMock()
        mock_tools.exact_lookup.return_value = []
        with patch("linguaalayam.mcp.remote.get_tools", return_value=mock_tools):
            remote.exact_lookup("run", ctx=MagicMock(), source="olam_enml")
        mock_tools.exact_lookup.assert_called_once_with("run", source="olam_enml")

    def test_fuzzy_lookup_passes_params(self):
        mock_tools = MagicMock()
        mock_tools.fuzzy_lookup.return_value = []
        with patch("linguaalayam.mcp.remote.get_tools", return_value=mock_tools):
            remote.fuzzy_lookup("run", ctx=MagicMock(), threshold=0.5, top_k=3, source="olam_enml")
        mock_tools.fuzzy_lookup.assert_called_once_with(
            "run", source="olam_enml", threshold=0.5, top_k=3
        )

    def test_semantic_lookup_passes_params(self):
        mock_tools = MagicMock()
        mock_tools.semantic_lookup.return_value = []
        with patch("linguaalayam.mcp.remote.get_tools", return_value=mock_tools):
            remote.semantic_lookup("meaning of life", ctx=MagicMock(), top_k=3, source="olam_enml")
        mock_tools.semantic_lookup.assert_called_once_with(
            "meaning of life", top_k=3, source="olam_enml"
        )


class TestGetMcpApp:
    """get_mcp_app's lazy singleton."""

    def test_returns_the_same_app_on_repeated_calls(self):
        remote._mcp_app = None
        first = remote.get_mcp_app()
        second = remote.get_mcp_app()
        assert first is second
        remote._mcp_app = None  # don't leak state into other tests

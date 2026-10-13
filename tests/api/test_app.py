"""Tests for api/app.py's background embedding-model loading wiring."""

import asyncio
import sys
from unittest.mock import MagicMock, patch

from linguaalayam.api.app import _init_tools, _load_embedding_service
from linguaalayam.embeddings.service import LazyEmbeddingService


class TestInitTools:
    """_init_tools builds DictionaryTools with a LazyEmbeddingService placeholder."""

    def test_returns_tools_and_lazy_service(self):
        """DictionaryTools should be usable immediately — its embedder is a
        LazyEmbeddingService, not a real (slow-to-construct) EmbeddingService."""
        with (
            patch("linguaalayam.api.app.build_engine"),
            patch("linguaalayam.api.app.build_session_factory"),
            patch("linguaalayam.api.app.set_session_factory"),
        ):
            tools, lazy_service = _init_tools()
        assert isinstance(lazy_service, LazyEmbeddingService)
        assert tools._embedder is lazy_service


class TestLoadEmbeddingService:
    """_load_embedding_service runs in the background and publishes the real service."""

    def test_constructs_and_publishes_real_service(self):
        """set_ready should be called with a real EmbeddingService once the
        (mocked) construction finishes."""
        lazy_service = LazyEmbeddingService()
        fake_model = MagicMock()
        fake_module = MagicMock(SentenceTransformer=lambda *a, **kw: fake_model)

        async def _run():
            with patch.dict(sys.modules, {"sentence_transformers": fake_module}):
                await _load_embedding_service(lazy_service)

        asyncio.run(_run())
        assert lazy_service._ready.is_set()
        assert lazy_service._service is not None

    def test_logs_and_does_not_raise_on_failure(self):
        """A construction failure should be logged, not propagated — an
        uncaught exception here would otherwise only surface as asyncio's
        generic 'Task exception was never retrieved' warning, with every
        semantic_lookup call left hanging forever with no clue why."""
        lazy_service = LazyEmbeddingService()

        def _boom(*_a, **_kw):
            raise RuntimeError("model download failed")

        fake_module = MagicMock(SentenceTransformer=_boom)

        async def _run():
            with (
                patch.dict(sys.modules, {"sentence_transformers": fake_module}),
                patch("linguaalayam.api.app.log") as mock_log,
            ):
                await _load_embedding_service(lazy_service)  # should not raise
            return mock_log

        mock_log = asyncio.run(_run())
        mock_log.error.assert_called_once()
        assert not lazy_service._ready.is_set()

"""Tests for the /admin/analytics dashboard: Basic Auth gating and the data pipeline."""

import datetime

import pytest
from fastapi.security import HTTPBasicCredentials
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from linguaalayam.api.admin import _fmt, _fmt_location, _require_admin, _window_start
from linguaalayam.api.app import app
from linguaalayam.observability.models import RequestLog


class TestRequireAdmin:
    """_require_admin's HTTP Basic Auth gate."""

    def test_raises_503_when_not_configured(self, monkeypatch):
        monkeypatch.delenv("ADMIN_USER", raising=False)
        monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
        with pytest.raises(Exception) as exc_info:
            _require_admin(HTTPBasicCredentials(username="a", password="b"))
        assert exc_info.value.status_code == 503

    def test_raises_401_for_wrong_credentials(self, monkeypatch):
        monkeypatch.setenv("ADMIN_USER", "admin")
        monkeypatch.setenv("ADMIN_PASSWORD", "secret")
        with pytest.raises(Exception) as exc_info:
            _require_admin(HTTPBasicCredentials(username="admin", password="wrong"))
        assert exc_info.value.status_code == 401

    def test_passes_for_correct_credentials(self, monkeypatch):
        monkeypatch.setenv("ADMIN_USER", "admin")
        monkeypatch.setenv("ADMIN_PASSWORD", "secret")
        _require_admin(HTTPBasicCredentials(username="admin", password="secret"))  # no raise


class TestFormatHelpers:
    """Pure display-formatting helpers."""

    def test_window_start_subtracts_minutes(self):
        start = _window_start(60)
        assert datetime.datetime.now(datetime.UTC) - start >= datetime.timedelta(minutes=60)

    def test_fmt_formats_as_utc(self):
        ts = datetime.datetime(2026, 9, 10, 20, 29)
        assert _fmt(ts) == "2026-09-10 20:29 UTC"

    def test_fmt_location_joins_present_parts(self):
        assert _fmt_location("Dresden", "Saxony", "DE") == "Dresden, Saxony, DE"

    def test_fmt_location_skips_missing_parts(self):
        assert _fmt_location(None, None, "DE") == "DE"

    def test_fmt_location_unknown_when_all_missing(self):
        assert _fmt_location(None, None, None) == "Unknown"


@pytest.fixture()
def admin_env(monkeypatch):
    """Set real admin credentials for the duration of a test."""
    monkeypatch.setenv("ADMIN_USER", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret")


@pytest.fixture()
def session_factory():
    """SQLite in-memory session factory with only the request_log table.

    Shared across threads (``StaticPool`` + ``check_same_thread=False``) since
    TestClient runs the endpoint in a worker thread.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    RequestLog.__table__.create(engine)
    yield sessionmaker(bind=engine)
    engine.dispose()


@pytest.fixture()
def client(admin_env, session_factory, monkeypatch):
    monkeypatch.setattr("linguaalayam.api.admin.get_session_factory", lambda: session_factory)
    return TestClient(app)


class TestAnalyticsPage:
    """/admin/analytics route-level auth gating."""

    def test_requires_auth(self, client):
        r = client.get("/admin/analytics")
        assert r.status_code == 401

    def test_rejects_wrong_credentials(self, client):
        r = client.get("/admin/analytics", auth=("admin", "wrong"))
        assert r.status_code == 401

    def test_serves_dashboard_shell_with_correct_credentials(self, client):
        r = client.get("/admin/analytics", auth=("admin", "secret"))
        assert r.status_code == 200


class TestAnalyticsPartial:
    """/admin/analytics/partial's real data pipeline, end-to-end against SQLite."""

    def test_requires_auth(self, client):
        r = client.get("/admin/analytics/partial")
        assert r.status_code == 401

    def test_renders_with_no_data(self, client):
        r = client.get("/admin/analytics/partial", auth=("admin", "secret"))
        assert r.status_code == 200

    def test_renders_real_search_rows(self, client, session_factory):
        with session_factory() as session:
            session.add(
                RequestLog(
                    method="GET",
                    path="/search",
                    route_type="web_search",
                    query="run",
                    status_code=200,
                    duration_ms=5.0,
                    ip="203.0.113.1",
                    city="Berlin",
                    region="Berlin",
                    country="DE",
                    user_agent="test",
                    is_bot=False,
                )
            )
            session.commit()

        r = client.get("/admin/analytics/partial", auth=("admin", "secret"))
        assert r.status_code == 200
        assert "run" in r.text
        assert "Berlin" in r.text

    def test_window_minutes_out_of_range_rejected(self, client):
        r = client.get(
            "/admin/analytics/partial", params={"window_minutes": 0}, auth=("admin", "secret")
        )
        assert r.status_code == 422

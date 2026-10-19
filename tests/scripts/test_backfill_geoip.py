"""Tests for backfill_geoip's core backfill logic."""

from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from linguaalayam.observability.models import RequestLog
from linguaalayam.scripts.backfill_geoip import backfill_geoip


@pytest.fixture()
def session():
    """SQLite in-memory session with only the request_log table."""
    engine = create_engine("sqlite:///:memory:")
    RequestLog.__table__.create(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()


def _row(session: Session, **overrides) -> RequestLog:
    """Insert a RequestLog row with sensible defaults, overridable per test."""
    defaults = {
        "method": "GET",
        "path": "/search",
        "route_type": "web_search",
        "query": "run",
        "status_code": 200,
        "duration_ms": 5.0,
        "ip": "203.0.113.1",
        "city": None,
        "region": None,
        "country": None,
        "user_agent": "test",
        "is_bot": False,
    }
    defaults.update(overrides)
    row = RequestLog(**defaults)
    session.add(row)
    session.commit()
    return row


def test_resolves_and_writes_a_matching_row(session):
    _row(session, ip="203.0.113.1")
    with patch(
        "linguaalayam.scripts.backfill_geoip.locate_ip",
        return_value=("Berlin", "Berlin", "DE"),
    ):
        scanned, resolved, unresolved = backfill_geoip(session)
    assert (scanned, resolved, unresolved) == (1, 1, 0)
    row = session.query(RequestLog).one()
    assert (row.city, row.region, row.country) == ("Berlin", "Berlin", "DE")


def test_dry_run_resolves_but_does_not_write(session):
    _row(session, ip="203.0.113.1")
    with patch(
        "linguaalayam.scripts.backfill_geoip.locate_ip",
        return_value=("Berlin", "Berlin", "DE"),
    ):
        scanned, resolved, unresolved = backfill_geoip(session, dry_run=True)
    assert (scanned, resolved, unresolved) == (1, 1, 0)
    row = session.query(RequestLog).one()
    assert row.city is None


def test_counts_unresolvable_rows_separately(session):
    _row(session, ip="203.0.113.1")
    with patch("linguaalayam.scripts.backfill_geoip.locate_ip", return_value=(None, None, None)):
        scanned, resolved, unresolved = backfill_geoip(session)
    assert (scanned, resolved, unresolved) == (1, 0, 1)


def test_keeps_existing_country_when_only_city_was_missing(session):
    """A real existing country is kept if the GeoIP lookup can't improve on it."""
    _row(session, ip="203.0.113.1", country="DE")
    with patch(
        "linguaalayam.scripts.backfill_geoip.locate_ip",
        return_value=("Berlin", "Berlin", None),
    ):
        backfill_geoip(session)
    row = session.query(RequestLog).one()
    assert row.country == "DE"


def test_skips_rows_already_resolved(session):
    _row(session, ip="203.0.113.1", city="Berlin")
    with patch("linguaalayam.scripts.backfill_geoip.locate_ip") as mock_locate:
        scanned, _, _ = backfill_geoip(session)
    assert scanned == 0
    mock_locate.assert_not_called()


def test_skips_rows_with_no_stored_ip(session):
    _row(session, ip=None)
    with patch("linguaalayam.scripts.backfill_geoip.locate_ip") as mock_locate:
        scanned, _, _ = backfill_geoip(session)
    assert scanned == 0
    mock_locate.assert_not_called()


def test_skips_route_types_no_dashboard_view_shows(session):
    _row(session, ip="203.0.113.1", route_type="static")
    with patch("linguaalayam.scripts.backfill_geoip.locate_ip") as mock_locate:
        scanned, _, _ = backfill_geoip(session)
    assert scanned == 0
    mock_locate.assert_not_called()

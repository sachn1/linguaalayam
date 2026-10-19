"""Tests for observability/queries.py's traffic/usage analytics query functions."""

import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from linguaalayam.observability.models import RequestLog
from linguaalayam.observability.queries import (
    log_request,
    searches_by_country,
    top_clients_simple,
    top_feature_usage,
    top_locations,
    top_outbound_clicks,
    top_queries_with_sources,
)

_NOW = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
_HOUR_AGO = _NOW - datetime.timedelta(hours=1)
_TWO_HOURS_AGO = _NOW - datetime.timedelta(hours=2)


@pytest.fixture()
def session():
    """SQLite in-memory session with only the request_log table created."""
    engine = create_engine("sqlite:///:memory:")
    RequestLog.__table__.create(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()


def _row(session: Session, **overrides) -> RequestLog:
    """Insert a RequestLog row with sensible defaults, overridable per test."""
    defaults = {
        "timestamp": _NOW,
        "method": "GET",
        "path": "/search",
        "route_type": "web_search",
        "query": "run",
        "status_code": 200,
        "duration_ms": 12.5,
        "ip": "203.0.113.1",
        "city": None,
        "region": None,
        "country": None,
        "user_agent": "test-agent",
        "is_bot": False,
    }
    defaults.update(overrides)
    row = RequestLog(**defaults)
    session.add(row)
    session.commit()
    return row


class TestLogRequest:
    """log_request's insert, via a real round-trip through the session."""

    def test_inserts_a_row_with_all_fields(self, session):
        log_request(
            session,
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
            user_agent="curl/8",
            is_bot=False,
        )
        session.commit()
        row = session.query(RequestLog).one()
        assert row.path == "/search"
        assert row.city == "Berlin"
        assert row.is_bot is False


class TestTopOutboundClicks:
    def test_counts_only_outbound_click_rows_in_window(self, session):
        _row(session, route_type="outbound_click", query="github", timestamp=_NOW)
        _row(session, route_type="outbound_click", query="github", timestamp=_NOW)
        _row(session, route_type="outbound_click", query="docs", timestamp=_NOW)
        _row(session, route_type="web_search", query="github", timestamp=_NOW)  # not a click

        result = top_outbound_clicks(session, since=_HOUR_AGO)
        assert result == [("github", 2), ("docs", 1)]

    def test_excludes_rows_before_the_window(self, session):
        _row(session, route_type="outbound_click", query="github", timestamp=_TWO_HOURS_AGO)
        assert top_outbound_clicks(session, since=_HOUR_AGO) == []

    def test_respects_limit(self, session):
        for label in ("a", "b", "c"):
            _row(session, route_type="outbound_click", query=label, timestamp=_NOW)
        assert len(top_outbound_clicks(session, since=_HOUR_AGO, limit=2)) == 2


class TestTopFeatureUsage:
    def test_counts_only_feature_route_types(self, session):
        _row(session, route_type="jayasree", query=None, timestamp=_NOW)
        _row(session, route_type="jayasree", query=None, timestamp=_NOW)
        _row(session, route_type="ml2en", query=None, timestamp=_NOW)
        _row(session, route_type="web_search", query="run", timestamp=_NOW)  # not a feature

        result = top_feature_usage(session, since=_HOUR_AGO)
        assert result == [("jayasree", 2), ("ml2en", 1)]


class TestTopQueriesWithSources:
    def test_groups_by_query_with_location_and_client_breakdown(self, session):
        _row(session, query="run", ip="1.1.1.1", city="Berlin", country="DE", timestamp=_NOW)
        _row(session, query="run", ip="2.2.2.2", city="Berlin", country="DE", timestamp=_NOW)
        _row(session, query="walk", ip="3.3.3.3", city="Paris", country="FR", timestamp=_NOW)

        result = top_queries_with_sources(session, since=_HOUR_AGO)
        by_query = {r[0]: r for r in result}

        run_query, run_count, run_locations, run_clients, _, _ = by_query["run"]
        assert run_count == 2
        assert run_locations == [("Berlin", None, "DE", 2)]
        assert run_clients == ["1.1.1.1", "2.2.2.2"]

        assert by_query["walk"][1] == 1

    def test_excludes_non_search_route_types(self, session):
        """Outbound-click/feature events reuse the `query` column but aren't search terms."""
        _row(session, route_type="outbound_click", query="github", timestamp=_NOW)
        result = top_queries_with_sources(session, since=_HOUR_AGO)
        assert result == []

    def test_excludes_empty_and_null_queries(self, session):
        _row(session, query="", timestamp=_NOW)
        _row(session, query=None, timestamp=_NOW)
        assert top_queries_with_sources(session, since=_HOUR_AGO) == []

    def test_ranks_by_total_count_descending(self, session):
        _row(session, query="rare", timestamp=_NOW)
        for _ in range(3):
            _row(session, query="common", timestamp=_NOW)

        result = top_queries_with_sources(session, since=_HOUR_AGO)
        assert [r[0] for r in result] == ["common", "rare"]


class TestSearchesByCountry:
    def test_counts_and_dedupes_queries_per_country(self, session):
        _row(session, country="DE", query="run", timestamp=_NOW)
        _row(session, country="DE", query="run", timestamp=_NOW)
        _row(session, country="DE", query="walk", timestamp=_NOW)
        _row(session, country="FR", query="run", timestamp=_NOW)

        result = {row[0]: row for row in searches_by_country(session, since=_HOUR_AGO)}
        assert result["DE"][1] == 3  # search_count
        assert result["DE"][2] == 2  # unique_queries
        assert result["FR"][1] == 1


class TestTopLocations:
    def test_groups_by_city_region_country(self, session):
        _row(session, city="Berlin", region="Berlin", country="DE", timestamp=_NOW)
        _row(session, city="Berlin", region="Berlin", country="DE", timestamp=_NOW)
        _row(session, city=None, region=None, country=None, timestamp=_NOW)  # unresolved

        result = {(r[0], r[1], r[2]): r for r in top_locations(session, since=_HOUR_AGO)}
        assert result[("Berlin", "Berlin", "DE")][3] == 2  # search_count
        assert result[(None, None, None)][3] == 1


class TestTopClientsSimple:
    def test_counts_by_ip_excluding_null(self, session):
        _row(session, ip="1.1.1.1", timestamp=_NOW)
        _row(session, ip="1.1.1.1", timestamp=_NOW)
        _row(session, ip=None, timestamp=_NOW)

        result = top_clients_simple(session, since=_HOUR_AGO)
        assert [(ip, count) for ip, count, _, _ in result] == [("1.1.1.1", 2)]

    def test_excludes_non_search_route_types(self, session):
        _row(session, ip="1.1.1.1", route_type="outbound_click", timestamp=_NOW)
        assert top_clients_simple(session, since=_HOUR_AGO) == []

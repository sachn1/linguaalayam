"""Query functions for request-level traffic and usage analytics."""

import datetime
from collections import Counter

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from linguaalayam.observability.models import RequestLog

_SEARCH_ROUTE_TYPES = ("web_search", "lookup_exact", "lookup_fuzzy", "lookup_semantic")


def log_request(
    session: Session,
    *,
    method: str,
    path: str,
    route_type: str,
    query: str | None,
    status_code: int,
    duration_ms: float,
    ip: str | None,
    country: str | None,
    user_agent: str | None,
    is_bot: bool,
) -> None:
    """Insert one traffic/usage analytics row for an inbound HTTP request.

    Parameters
    ----------
    session : Session
        SQLAlchemy session to use for the insert.
    method : str
        HTTP method (e.g. "GET").
    path : str
        Request path, excluding query string.
    route_type : str
        Coarse route category (e.g. "web_search", "lookup_exact", "mcp", "other").
    query : str | None
        Search term extracted from the ``query`` query-string parameter, if present.
    status_code : int
        HTTP response status code.
    duration_ms : float
        Request handling time in milliseconds.
    ip : str | None
        Client IP address.
    country : str | None
        Two-letter country code, if available.
    user_agent : str | None
        Raw User-Agent header.
    is_bot : bool
        Heuristic guess that the request is automated.
    """
    session.add(
        RequestLog(
            method=method,
            path=path,
            route_type=route_type,
            query=query,
            status_code=status_code,
            duration_ms=duration_ms,
            ip=ip,
            country=country,
            user_agent=user_agent,
            is_bot=is_bot,
        )
    )


def top_outbound_clicks(
    session: Session, since: datetime.datetime, limit: int = 10
) -> list[tuple[str, int]]:
    """Return click counts for outbound links (How to use, GitHub, etc.) since a timestamp.

    Parameters
    ----------
    session : Session
        SQLAlchemy session to use for the query.
    since : datetime.datetime
        Only count requests logged at or after this timestamp.
    limit : int, optional
        Maximum number of labels to return, by default 10
    """
    stmt = (
        select(RequestLog.query, func.count().label("count"))
        .where(RequestLog.timestamp >= since, RequestLog.route_type == "outbound_click")
        .group_by(RequestLog.query)
        .order_by(desc("count"))
        .limit(limit)
    )
    return [(row.query, row.count) for row in session.execute(stmt)]


def top_queries_with_sources(
    session: Session, since: datetime.datetime, limit: int = 20
) -> list[tuple[str, int, list[tuple[str, int]], list[str], datetime.datetime, datetime.datetime]]:
    """Return the most frequent search terms with a per-query country/client/time breakdown.

    Restricted to search/lookup route types so outbound-click labels and feature
    events (which reuse the same ``query`` column — see ``RequestLog.query``)
    don't get attributed to a search term's sources.

    Parameters
    ----------
    session : Session
        SQLAlchemy session to use for the query.
    since : datetime.datetime
        Only count requests logged at or after this timestamp.
    limit : int, optional
        Maximum number of terms to return, by default 20

    Returns
    -------
    list[tuple[str, int, list[tuple[str, int]], list[str], datetime, datetime]]
        ``(query, total_count, countries, clients, first_seen, last_seen)`` tuples,
        ordered by total count descending. ``countries`` is a list of
        ``(country, count)`` pairs sorted by count descending (missing values
        grouped under "Unknown"); ``clients`` is a sorted list of the distinct
        client IPs that issued that query; ``first_seen``/``last_seen`` are the
        earliest/latest timestamps for that query in the window.
    """
    stmt = select(RequestLog.query, RequestLog.country, RequestLog.ip, RequestLog.timestamp).where(
        RequestLog.timestamp >= since,
        RequestLog.route_type.in_(_SEARCH_ROUTE_TYPES),
        RequestLog.query.isnot(None),
        RequestLog.query != "",
    )

    by_query: dict[str, dict] = {}
    for query, country, ip, timestamp in session.execute(stmt):
        entry = by_query.setdefault(
            query,
            {
                "count": 0,
                "countries": Counter(),
                "clients": set(),
                "first_seen": timestamp,
                "last_seen": timestamp,
            },
        )
        entry["count"] += 1
        entry["countries"][country or "Unknown"] += 1
        if ip:
            entry["clients"].add(ip)
        entry["first_seen"] = min(entry["first_seen"], timestamp)
        entry["last_seen"] = max(entry["last_seen"], timestamp)

    ranked = sorted(by_query.items(), key=lambda item: item[1]["count"], reverse=True)[:limit]
    return [
        (
            query,
            data["count"],
            sorted(data["countries"].items(), key=lambda kv: kv[1], reverse=True),
            sorted(data["clients"]),
            data["first_seen"],
            data["last_seen"],
        )
        for query, data in ranked
    ]


def searches_by_country(
    session: Session, since: datetime.datetime, limit: int = 20
) -> list[tuple[str | None, int, int, datetime.datetime, datetime.datetime]]:
    """Return search counts grouped by country since a given timestamp.

    Restricted to search/lookup route types so outbound clicks and feature
    events don't inflate a country's search count.

    Parameters
    ----------
    session : Session
        SQLAlchemy session to use for the query.
    since : datetime.datetime
        Only count requests logged at or after this timestamp.
    limit : int, optional
        Maximum number of countries to return, by default 20

    Returns
    -------
    list[tuple[str | None, int, int, datetime, datetime]]
        ``(country, search_count, unique_queries, first_seen, last_seen)`` tuples,
        ordered by search count.
    """
    stmt = (
        select(
            RequestLog.country,
            func.count().label("search_count"),
            func.count(func.distinct(RequestLog.query)).label("unique_queries"),
            func.min(RequestLog.timestamp).label("first_seen"),
            func.max(RequestLog.timestamp).label("last_seen"),
        )
        .where(RequestLog.timestamp >= since, RequestLog.route_type.in_(_SEARCH_ROUTE_TYPES))
        .group_by(RequestLog.country)
        .order_by(desc("search_count"))
        .limit(limit)
    )
    return [
        (row.country, row.search_count, row.unique_queries, row.first_seen, row.last_seen)
        for row in session.execute(stmt)
    ]


def top_clients_simple(
    session: Session, since: datetime.datetime, limit: int = 10
) -> list[tuple[str, int, datetime.datetime, datetime.datetime]]:
    """Return the most active clients (by IP) since a given timestamp.

    Restricted to search/lookup route types so outbound clicks and feature
    events don't inflate a client's search count.

    Parameters
    ----------
    session : Session
        SQLAlchemy session to use for the query.
    since : datetime.datetime
        Only count requests logged at or after this timestamp.
    limit : int, optional
        Maximum number of clients to return, by default 10

    Returns
    -------
    list[tuple[str, int, datetime, datetime]]
        ``(ip, count, first_seen, last_seen)`` tuples, ordered by count descending.
    """
    stmt = (
        select(
            RequestLog.ip,
            func.count().label("count"),
            func.min(RequestLog.timestamp).label("first_seen"),
            func.max(RequestLog.timestamp).label("last_seen"),
        )
        .where(
            RequestLog.timestamp >= since,
            RequestLog.ip.isnot(None),
            RequestLog.route_type.in_(_SEARCH_ROUTE_TYPES),
        )
        .group_by(RequestLog.ip)
        .order_by(desc("count"))
        .limit(limit)
    )
    return [(row.ip, row.count, row.first_seen, row.last_seen) for row in session.execute(stmt)]

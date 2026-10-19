"""One-off backfill: resolve city/region/country for request_log rows that predate GeoIP lookup."""

import hydra
from omegaconf import DictConfig, OmegaConf
from sqlalchemy import select
from sqlalchemy.orm import Session

from linguaalayam.database import build_engine, build_session_factory, get_session
from linguaalayam.env import load_env
from linguaalayam.observability.geoip import locate_ip
from linguaalayam.observability.models import RequestLog
from linguaalayam.observability.queries import LOCATION_RELEVANT_ROUTE_TYPES

load_env()


def backfill_geoip(session: Session, *, dry_run: bool = False) -> tuple[int, int, int]:
    """Resolve city/region/country for request_log rows with a stored IP but no city.

    Only touches rows whose ``route_type`` some dashboard view actually groups/filters
    by (``LOCATION_RELEVANT_ROUTE_TYPES``) — older rows logged under a route_type no
    current view displays by location have nothing to gain from resolving. Rows whose
    IP was never a real client address (e.g. an internal metadata-service hop) simply
    have nothing to backfill and stay "Unknown".

    Parameters
    ----------
    session : Session
        SQLAlchemy session to scan and (unless ``dry_run``) write to.
    dry_run : bool, optional
        When True, print what would change but don't write it, by default False.

    Returns
    -------
    tuple[int, int, int]
        ``(scanned, resolved, unresolved)`` row counts.
    """
    scanned = resolved = unresolved = 0
    stmt = select(RequestLog).where(
        RequestLog.city.is_(None),
        RequestLog.ip.isnot(None),
        RequestLog.route_type.in_(LOCATION_RELEVANT_ROUTE_TYPES),
    )
    for row in session.execute(stmt).scalars():
        scanned += 1
        city, region, country = locate_ip(row.ip)
        if city is None and country is None:
            unresolved += 1
            continue
        resolved += 1
        print(f"  {row.ip:<40} -> {city}, {region}, {country}")
        if not dry_run:
            row.city = city
            row.region = region
            row.country = row.country or country

    if dry_run:
        session.rollback()
    return scanned, resolved, unresolved


@hydra.main(config_path="../../config", config_name="config", version_base=None)
def main(cfg: DictConfig) -> None:  # pragma: no cover
    """Backfill city/region/country for request_log rows with a stored IP but no city."""
    dry_run: bool = OmegaConf.select(cfg, "dry_run", default=False)

    engine = build_engine(cfg.database)
    session_factory = build_session_factory(engine)

    with get_session(session_factory) as session:
        scanned, resolved, unresolved = backfill_geoip(session, dry_run=dry_run)

    print(
        f"\nScanned {scanned} rows with a stored IP, no city, and a "
        f"dashboard-relevant route_type. Resolved {resolved}, left {unresolved} "
        f"unresolved (no location data for that IP)."
        + (" [dry run — no changes written]" if dry_run else "")
    )

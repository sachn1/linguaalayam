"""One-off backfill: resolve city/region (and country where missing) for
existing request_log rows that predate the GeoIP lookup.

Only touches rows with a real stored IP and no city yet — rows whose IP was
never a real client address (e.g. an internal 169.254.x.x metadata-service
hop, logged by a since-fixed bug in client_ip()) simply have nothing to
backfill and are left as "Unknown", same as before.

Usage (point DB_HOST/DB_PORT at wherever the target Postgres is reachable,
e.g. through an SSH tunnel for production):
    poetry run backfill-geoip
    poetry run backfill-geoip +dry_run=true
"""

import hydra
from omegaconf import DictConfig, OmegaConf
from sqlalchemy import select

from linguaalayam.database import build_engine, build_session_factory, get_session
from linguaalayam.env import load_env
from linguaalayam.observability.geoip import locate_ip
from linguaalayam.observability.models import RequestLog

load_env()


@hydra.main(config_path="../../config", config_name="config", version_base=None)
def main(cfg: DictConfig) -> None:  # pragma: no cover
    """Backfill city/region/country for request_log rows with a stored IP but no city."""
    dry_run: bool = OmegaConf.select(cfg, "dry_run", default=False)

    engine = build_engine(cfg.database)
    session_factory = build_session_factory(engine)

    scanned = resolved = unresolved = 0
    with get_session(session_factory) as session:
        stmt = select(RequestLog).where(RequestLog.city.is_(None), RequestLog.ip.isnot(None))
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

    print(
        f"\nScanned {scanned} rows with a stored IP and no city. "
        f"Resolved {resolved}, left {unresolved} unresolved (no location data for that IP)."
        + (" [dry run — no changes written]" if dry_run else "")
    )

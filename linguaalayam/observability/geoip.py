"""IP -> city/region/country lookup via a local MaxMind GeoLite2-City database.

Cloud Run has no equivalent of Cloudflare's ``CF-IPCountry`` header, so since
the app moved off Cloudflare-proxied DNS, country (and now city/region) comes
from a local ``.mmdb`` lookup instead of a free upstream header.
"""

import logging
import os
import threading

import geoip2.database
import geoip2.errors

log = logging.getLogger(__name__)

_DB_PATH = os.getenv("GEOIP_DB_PATH", "data/geoip/GeoLite2-City.mmdb")

_reader: geoip2.database.Reader | None = None
_reader_lock = threading.Lock()
_warned_missing = False


def _get_reader() -> geoip2.database.Reader | None:
    """Lazily open the MaxMind database reader, or None if it's unavailable.

    The reader wraps an mmap'd file and is safe to share across threads once
    open, so this only needs to run once per process.
    """
    global _reader, _warned_missing
    if _reader is not None:
        return _reader
    with _reader_lock:
        if _reader is None:
            if not os.path.exists(_DB_PATH):
                if not _warned_missing:
                    log.warning(
                        "GeoIP database not found at %s — location fields will be empty. "
                        "See .env.example for GEOIP_DB_PATH / download instructions.",
                        _DB_PATH,
                    )
                    _warned_missing = True
                return None
            _reader = geoip2.database.Reader(_DB_PATH)
    return _reader


def locate_ip(ip: str | None) -> tuple[str | None, str | None, str | None]:
    """Return ``(city, region, country_code)`` for an IP, or all-None on any miss.

    Parameters
    ----------
    ip : str | None
        Client IP to look up. Private/reserved addresses and lookup misses
        (e.g. the database file is absent) resolve to ``(None, None, None)``
        rather than raising — a dashboard with a few "Unknown" rows is far
        better than a request failing because analytics couldn't resolve one.
    """
    if not ip:
        return None, None, None
    reader = _get_reader()
    if reader is None:
        return None, None, None
    try:
        result = reader.city(ip)
    except (geoip2.errors.AddressNotFoundError, ValueError):
        return None, None, None
    city = result.city.name
    region = result.subdivisions.most_specific.name
    country = result.country.iso_code
    return city, region, country

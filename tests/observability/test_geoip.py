"""Tests for the graceful-miss behavior in observability/geoip.py.

No real .mmdb fixture is shipped with the repo (it's a third-party download,
not a build artifact — see .env.example), so these only cover the paths that
don't require an actual database file: a missing IP, and a missing database.
"""

from linguaalayam.observability.geoip import locate_ip


class TestLocateIp:
    """locate_ip degrades to (None, None, None) rather than raising."""

    def test_none_ip_short_circuits(self):
        """A None IP never attempts a lookup."""
        assert locate_ip(None) == (None, None, None)

    def test_missing_database_degrades_gracefully(self, monkeypatch):
        """A nonexistent GEOIP_DB_PATH resolves to all-None, not an exception."""
        import linguaalayam.observability.geoip as geoip_module

        monkeypatch.setattr(geoip_module, "_DB_PATH", "/nonexistent/GeoLite2-City.mmdb")
        monkeypatch.setattr(geoip_module, "_reader", None)
        monkeypatch.setattr(geoip_module, "_warned_missing", False)

        assert locate_ip("8.8.8.8") == (None, None, None)

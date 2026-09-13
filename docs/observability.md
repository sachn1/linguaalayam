# Observability

LinguAalayam collects usage analytics through two channels: server-side HTTP request logging and client-side feature event tracking. All data flows into a single `request_log` table, consumed by the admin dashboard at `/admin/analytics`.

## Architecture

```
HTTP request → RequestLoggingMiddleware (ASGI) → request_log table
Client click → sendBeacon → POST /track/click → request_log table
Varnam fallback → log_feature_event() → request_log table
                                     ↓
                        /admin/analytics (HTMX dashboard, Basic Auth)
```

## Request logging

`RequestLoggingMiddleware` in `observability/middleware.py` is an ASGI middleware that only logs **real search bar queries** — requests to `/search` with a non-empty `query` parameter from non-bot clients. Everything else (static assets, API docs, health probes, MCP traffic, empty typing, bots/scrapers) is intentionally ignored. Cloudflare already covers general traffic analytics.

| Field | Description |
|---|---|
| `id` | Autoincrement PK |
| `timestamp` | Server time of the request |
| `path` | URL path (always `/search`) |
| `route_type` | Always `web_search` for logged rows |
| `method` | HTTP method (always `GET`) |
| `status_code` | Response status |
| `duration_ms` | Request duration in milliseconds |
| `ip` | Client IP address |
| `country` | Country code from `CF-IPCountry` header |
| `query` | The search term |
| `user_agent` | Browser/client user agent string |
| `is_bot` | Always `False` (bots are filtered out before logging) |

Click tracking via `POST /track/click` and `log_feature_event()` still write rows for feature interactions (jayasree, varnam, outbound clicks, etc.) — only the generic middleware is filtered.

## Click tracking

Client-side interactions that don't have their own server route (e.g. clicking a jayasree trace button, toggling romanisation, clicking outbound links) are reported via `navigator.sendBeacon` to `POST /track/click`. The endpoint in `observability/router.py` validates the event label against an allow-list and writes a `request_log` row with `route_type` set to the label.

The `sendBeacon` call is fired in `onclick` handlers across templates:
```js
function trackClick(label) {
  navigator.sendBeacon('/track/click', JSON.stringify({ label }));
}
```

## Feature events

For server-side feature usage that isn't tied to a specific HTTP request (e.g. Varnam manglish fallback triggered inside `/search`), `log_feature_event()` in `observability/events.py` writes a `request_log` row directly with `route_type='varnam'` and the original request's IP/UA extracted from context.

## Admin dashboard

The dashboard at `/admin/analytics` is served by `api/admin.py`, gated by HTTP Basic Auth (`ADMIN_USER` / `ADMIN_PASSWORD`). It uses HTMX polling to refresh metrics every 30 seconds.

Available metrics:
- **Total searches** — count of real search queries in the window
- **Unique queries** — how many distinct search terms
- **Top queries** — most searched terms, with per-query country/client breakdown and first/last-seen timestamps
- **By country** — search counts and unique queries per country, with first/last-seen timestamps
- **Outbound clicks** — most clicked external links
- **Top clients** — most active client IPs, with first/last-seen timestamps

The JSON partial is at `/admin/analytics/partial` for programmatic access.

## Query helpers

`observability/queries.py` provides reusable query functions:

| Function | Description |
|---|---|
| `top_queries_with_sources(session, since, limit)` | Most frequent search queries, each with a per-country/per-client breakdown and first/last-seen timestamps |
| `searches_by_country(session, since, limit)` | Search counts and unique queries per country, with first/last-seen timestamps |
| `top_outbound_clicks(session, since, limit)` | Most clicked outbound links |
| `top_clients_simple(session, since, limit)` | Most active client IPs, with first/last-seen timestamps |

## Adding a new event type

1. Add a `route_type` string to the allow-list in `observability/router.py` (for click tracking) or call `log_feature_event()` directly in your handler.
2. If you need a new dashboard widget, add a query function in `observability/queries.py` and render it in `admin_analytics.html`.

# Security Policy

## Supported versions

Only the latest release on `master` receives security fixes.

| Version | Supported |
|---|---|
| Latest (`master`) | ✅ |
| Older releases | ❌ |

## Scope

LinguAalayam is a read-only Malayalam dictionary. It does not handle user accounts, payments, or sensitive personal data. The primary attack surfaces are:

- The FastAPI REST/web layer (injection, path traversal, DoS)
- The MCP OAuth endpoints (token forgery, scope escalation)
- User-supplied API keys stored in browser `localStorage` (client-side only — never sent to our servers)

## Reporting a vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Report privately via [GitHub Security Advisories](https://github.com/sachn1/linguaalayam/security/advisories/new). Include:

- Description of the vulnerability and its potential impact
- Steps to reproduce or a proof-of-concept
- Affected version or commit

You will receive an acknowledgement within 72 hours. We aim to release a fix within 14 days for critical issues.

## Out of scope

- Vulnerabilities in third-party dependencies (report to the upstream project)
- Issues that require physical access to the server
- Social engineering
- Denial-of-service via high query volume (rate limiting is a known gap, tracked in backlog)

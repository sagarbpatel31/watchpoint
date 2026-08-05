# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in Watchpoint, please report it
**privately** rather than opening a public issue.

You can report vulnerabilities by:

1. Opening a [private security advisory](https://github.com/sagarbpatel31/watchpoint/security/advisories/new) on GitHub (preferred)
2. Or contacting the maintainer directly via the GitHub profile

### What to include

- A clear description of the vulnerability
- Steps to reproduce
- Affected files / endpoints / versions
- Potential impact
- Any suggested mitigations

### Response timeline

We aim to:

- **Acknowledge** your report within **48 hours**
- **Provide a status update** within **7 days**
- **Issue a fix** for critical issues within **14 days**

## Supported Versions

This is an early-stage project. Only the `main` branch receives security updates.

| Version | Supported |
| ------- | --------- |
| `main`  | ✅        |
| Other   | ❌        |

## Security Considerations for Users

If you're running Watchpoint locally or in production:

- **Always set `JWT_SECRET_KEY`** to a strong random value via environment variable.
  Generate one with: `openssl rand -hex 32`
- **Never commit `.env` files** — use `.env.example` as a template
- **Change the demo user password** (`demo@watchpoint.ai` / `demo123`) before
  deploying anywhere accessible from the internet
- **Use TLS** in production — terminate at your load balancer or reverse proxy
- **Restrict CORS_ORIGINS** to only the domains that need access to the API

Thank you for helping keep Watchpoint and its users safe.

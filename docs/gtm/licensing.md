# Licensing and the open-core boundary

Decided: 2026-08-05. Owner: Sagar Patel.

---

## Decision

**The Watchpoint core is Apache License 2.0.** Commercial features are licensed
separately and live outside the Apache-licensed tree.

This replaced the previous *TraceMind Source-Available License*, which permitted
"reference, evaluation, and educational purposes only" and forbade commercial use
without written permission.

## Why the old license had to go

It was incompatible with the go-to-market strategy in three specific ways:

1. **Design partners could not legally run it.** A robotics company deploying
   Watchpoint on a production fleet is commercial use. Every partner would have
   needed a bilateral written grant before writing a line of integration code —
   friction at exactly the moment you want none.
2. **A free Community tier was not permissible.** "Free, self-hosted, forever,
   unlimited devices" cannot be offered under a license that forbids commercial
   use.
3. **It defeated the trust argument.** The self-hosted wedge rests on "read the
   collector before you put it on a robot." An evaluation-only license invites
   engineers to read the code and then forbids them from using it, which is worse
   for credibility than closed source.

It also still carried the name *TraceMind* and pointed at a repository URL that no
longer resolves.

## Why Apache 2.0 specifically

- **Passes security review without a lawyer.** Robotics buyers have Apache 2.0 on
  their pre-approved list. A custom license triggers legal review and adds weeks
  to a deal that hasn't started yet.
- **Explicit patent grant.** Matters more than usual in robotics, where buyers are
  patent-sensitive and building safety cases.
- **Permissive enough to get onto robots.** Adoption is the scarce resource at
  this stage, not defensibility.

**The accepted cost:** a competitor can fork the core. At current scale that risk
is dominated by the risk of nobody using it at all. Revisit if a hosted
competitor appears — the fallback is BSL 1.1 with a delayed Apache conversion,
applied to *new* releases only.

---

## The open-core boundary

Everything currently in the repository is Apache 2.0. The boundary matters for
what gets built next, so it is defined up front.

### Apache 2.0 — the core, permanently

| Component | Path |
|-----------|------|
| Model collector and all framework adapters | `agents/model-collector/` |
| ROS 2 collector | `agents/ros2-collector/` |
| Go edge agent | `agents/edge-agent/` |
| API, data model, ingest and query endpoints | `apps/api/` |
| System rules engine (7 rules) | `apps/api/app/services/analysis.py` |
| AI rules engine and the rules themselves | `apps/api/app/rca/` |
| Web dashboard, incident and inference views | `apps/web/` |
| Replay bundle export | `apps/api/app/services/replay_bundle.py` |
| Sample data and seeds | `packages/sample-data/` |

**Rule of thumb:** anything that runs on a customer's robot is Apache 2.0,
without exception. A collector nobody can audit is a collector nobody will
install.

### Commercial — separately licensed, kept out of this tree

These are not yet built. When they are, they go in a separate directory with
their own LICENSE, or a separate repository:

- SSO / SAML and audit logging
- Cross-fleet baselines and multi-tenant fleet rollups
- Managed hosted offering (control plane, billing, tenancy)
- Compliance and safety-case record exports
- Long-term retention tiering

### Deliberately *not* commercial

Some things are tempting to gate and shouldn't be, because gating them breaks the
product's core promise:

- **The AI rule taxonomy.** The rules *are* the argument. Gating AI-004…AI-008
  would mean the free tier can't detect most failures, which makes the free tier
  a demo rather than a product.
- **Data export.** Never hold a customer's incident data hostage. Self-hosted
  means they already have the Postgres.
- **Any collector.** See above.

The Team tier earns its price on fleet-scale analysis, the replay sandbox, and
support — not on withholding detection.

---

## Follow-up actions

| # | Action | Owner | Status |
|---|--------|-------|--------|
| 1 | Replace LICENSE with Apache 2.0 | Claude | ✅ done |
| 2 | Align site copy with the new license | Claude | ✅ done |
| 3 | Add SPDX headers to source files | — | open, low priority |
| 4 | Add a `NOTICE` file if third-party Apache code is ever vendored | — | not needed yet |
| 5 | Confirm no prior contributor assigned rights under the old license | Sagar | **open — verify before announcing** |
| 6 | Decide whether a CLA/DCO is required for outside contributors | Sagar | open |

Action 5 matters: relicensing is only clean if you hold copyright on everything
in the tree. Solo-authored work is fine. If anyone else has contributed, get their
sign-off in writing before publicising the license change.

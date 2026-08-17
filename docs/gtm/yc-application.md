# YC Application — Watchpoint

Draft. Last updated: 2026-08-05.

**How to use this file.** Product, market, and competitive answers are written and
ready. Anything marked **`[SAGAR]`** is a fact only you can supply — founder
history, dates, entity status. Do not submit with placeholders in place, and do
not soften the traction answers: YC partners read thousands of these and reward
candour far more than polish. The fastest way to fail the interview is to have
written something in October that stopped being true in September.

---

## Company

**Company name**
Watchpoint

**Describe what your company does in 50 characters or less.**
> `AI failure forensics for robots` *(31 characters)*

Alternates, all under 50:
- `We tell you why your robot's AI failed` (37)
- `Root-cause analysis for robot AI failures` (40)
- `Black box recorder for the AI on your robot` (43)

**Company URL**
`[SAGAR]` — the live Vercel deployment. Point this at the production frontend
once P1 deploy is done, not at a preview URL.

**Demo video (1 minute, founders on camera)**
Not yet recorded. See "Demo video script" at the bottom of this file.

**Please provide a link to the product, if any.**
Repository: https://github.com/sagarbpatel31/watchpoint
Live demo: `[SAGAR]` — hosted demo, no signup required.

---

## The product

### What is your company going to make?

Watchpoint is failure forensics for the AI layer of robots.

When a robot fails in the field today, an engineer opens their dashboards and
finds that CPU, memory, thermals, and every ROS 2 topic were completely normal.
Nothing threw an exception. The code ran perfectly and returned a wrong answer.
So they pull the rosbag and scrub through it by hand until they find the frame —
and that takes days.

The reason it takes days is that the four things that would explain the failure
are thrown away every frame:

1. **What the model saw** — the synced camera, lidar, and depth frames at inference time
2. **What it predicted** — outputs, per-class confidence, attention maps
3. **What the policy decided** — the chosen action and the alternatives it ranked
4. **Whether the input was novel** — how far the input sat from the training distribution

Watchpoint captures all four. A collector attaches forward hooks to the model and
keeps a fixed-size ring buffer in-process, designed for under 1% overhead at p99.
Nothing is transmitted until an incident triggers; then the buffer flushes and the
model timeline is joined to system telemetry, ROS 2 topic health, and the exact
weights hash that was deployed.

On top of that we run a rules engine that *names* the failure instead of handing
you charts — `AI-001: perception confidence collapse`, `AI-002: input 2.7σ out of
distribution`, `AI-005: policy chose an action incompatible with a
high-confidence detection`. Then you replay the captured inputs against new
weights to prove the fix before it reaches the fleet.

The short version: **a black box recorder for the AI on your robot, plus the
accident investigator.**

### Why did you pick this idea to work on? Do you have domain expertise?

`[SAGAR — this is the single most important answer in the application. It must be
a specific story, not a thesis. Answer these four and write the true version:]`

- *What is the specific incident you personally lost days to?* Name the robot, the
  failure, what the dashboards said, and how you eventually found the cause. YC
  partners can tell instantly whether a founder has lived the problem.
- *What is your robotics / ML background?* Companies, years, what you shipped, what
  broke.
- *Who have you already talked to about this?* Number of robotics engineers, and the
  most surprising thing one of them told you. If the number is zero, go do fifteen
  conversations before submitting — this answer is unwritable without them.
- *Why you specifically?* What do you know that the next person to try this doesn't?

**The claim that must be true and defensible:** teams building physical AI debug
their models by reconstructing behaviour from downstream side effects, because
nothing retains the model's internal state at failure time. That is a solvable
engineering problem that nobody has productised for robotics.

### How do you know people need what you're making?

`[SAGAR — replace with real evidence.]` Strongest to weakest:

1. Design partners running it on real fleets, with a quote about time saved
2. Named engineers at named companies who described the problem unprompted
3. Public evidence: robotics teams building this internally, conference talks about
   field debugging, job postings for "robot data infrastructure"

Do not answer this with market-size reasoning. YC reads TAM-as-evidence as a
signal you haven't talked to users.

### What's new about what you're making?

Three things, in order of defensibility:

1. **The taxonomy.** AI-001 through AI-008 is a named, testable classification of
   how learned perception and policy fail in the physical world. The plumbing is
   replicable; agreeing on what the failure modes *are* — and encoding them as
   rules that fire on real telemetry — is the hard part and the accumulating asset.
2. **Model-layer capture at the edge, cheaply.** Ring-buffered, in-process,
   flushed only on incident. The naive approach — record everything always — is
   unaffordable at fleet scale, which is why teams sample and then miss the frame
   that mattered.
3. **Joining model state to system state on one timeline.** Existing tools own one
   side or the other. The diagnosis usually lives in the correlation: the input
   went out-of-distribution *because* the lens fogged, which shows up as an image
   sharpness drop nobody was watching.

### Who are your competitors? What do you understand that they don't?

| Category | Who | The gap |
|----------|-----|---------|
| Infra monitoring | Datadog, Grafana, Prometheus | Model is a black box. "CPU normal" is precisely the misleading signal |
| Robotics visualisation | Foxglove, Rerun, rosbag tooling | Excellent viewers, but you must already know what to look for. No model introspection, no automated root cause |
| ML observability | Arize, WhyLabs, Fiddler | Built for server-side batch inference. No hard real-time constraint, no sensor sync, no incident model, no edge deployment |
| Experiment tracking | Weights & Biases, MLflow | Stops at deployment |
| Error tracking | Sentry | AI failures throw nothing |
| **In-house tooling** | **Every serious robotics team** | **The actual competitor** |

**What we understand that they don't:**

1. **In the failures that matter, infrastructure telemetry is clean.** Tools built
   on the premise that resource health predicts failure are structurally blind
   here. It's a modelling assumption baked into the product, not a feature gap.

2. **Robotics AI failures are single events, not distributions.** ML observability
   assumes drift is gradual and detected across a population. A robot's failure is
   one 200ms window with one specific frame in it. You need forensics on that
   event, not aggregate monitoring.

3. **The data cannot leave the building.** Camera footage from a customer's
   warehouse is routinely un-exportable by contract. Every SaaS-first ML
   observability vendor hits this wall in robotics. We ship self-hosted,
   Apache 2.0, no outbound dependency — the security review that kills other
   vendors is the one we're designed to pass.

4. **In-house wins on fit and loses on sustained attention.** Teams do build this.
   It costs one to two engineers indefinitely and it is the first thing cut when a
   customer deadline lands. We're competing with a project that is always someone's
   second priority.

---

## Progress

> **Answer these with today's truth on the day you submit.** As of 2026-08-05 the
> honest position is: working product, no users, no revenue. That is a normal
> place to apply from. Inflating it is not survivable — YC will ask for the
> customer's name.

### How far along are you?

Working end-to-end system, self-hosted, with a live demo. Built and merged:

- **Model collector** (Python) — PyTorch forward hooks, thread-safe ring buffer, msgpack writer, HTTP flush. 16 tests passing.
- **Backend** (FastAPI, Postgres, SQLAlchemy async) — auth, devices, incidents, projects, telemetry ingest, AI-layer ingest and query. Alembic migrations. 35 tests passing.
- **Rules engines** — 7 system rules, plus AI-001, AI-002, AI-003 against captured model state. Optional LLM incident summary that degrades to deterministic rules text with no API key.
- **Frontend** (Next.js 16, TypeScript) — dashboard, incident timeline, device views, inference detail with an inference timeline.
- **Collectors** — ROS 2 topic/node/lag monitor; Go edge agent for host metrics.
- **Replay bundles** — portable ZIP export of all incident evidence.
- **Demo** — three seeded incidents, each carrying both system telemetry and captured AI-layer inferences.

**Honest about what is not built:** rules AI-004 through AI-008 are specified but
not merged; the deterministic replay sandbox, Grad-CAM attention endpoint, and
hosted cloud are roadmap. The edge agent still simulates some host metrics.
Ingest endpoints are not yet authenticated, which is the gate before any external
fleet can send data.

### How long have you been working on this?

`[SAGAR]` — start date, and how much has been full-time. Be exact.

### Are people using your product?

`[SAGAR]` — as of this draft, no external users. If that's still true at
submission, say so plainly and follow with the design-partner pipeline: how many
conversations, how many committed. See `docs/gtm/design-partners.md`.

### Do you have revenue?

`[SAGAR]` — no revenue as of this draft.

### What tech stack are you using?

Python 3.11 / FastAPI / SQLAlchemy 2.0 async / asyncpg / Postgres; Next.js 16 /
TypeScript / Tailwind / shadcn on the frontend; Go for the edge agent; PyTorch
hooks in the collector; Alembic for migrations; Docker Compose for self-hosted
deployment. Apache 2.0.

### Have you formed a legal entity yet?

`[SAGAR]`

### Incubators / accelerators

`[SAGAR]`

---

## Business

### How will you make money? How much could you make?

**Model:** open-core, priced per robot per month. Full detail in
`docs/gtm/positioning.md` and the pricing page.

- **Community** — free, self-hosted, Apache 2.0. The complete forensics core.
- **Team** — $49 per robot / month billed annually, 10-robot minimum. Fleet-scale analysis, replay sandbox, priority support.
- **Enterprise** — custom. SSO, air-gapped deployment, safety-case exports, custom rules, SLA.

Per-robot rather than per-gigabyte is deliberate: volume pricing makes customers
capture less exactly when they should capture more, and the entire product depends
on the failure frame being in the buffer.

**Illustrative account economics** — clearly labelled as modelled, not observed:
a Series A robotics company with a 40-robot fleet on Team is ~$23.5k ARR. A
200-robot Series B on Enterprise is plausibly $100k+. That puts the mid-market
ACV in the $25k–$100k range, which supports a founder-led sales motion without
requiring an enterprise sales team on day one.

**Market:** bottom-up, not TAM-down. Commercial deployed fleets in warehouse
robotics, agriculture, delivery, and inspection number in the low thousands of
companies. Assume ~2,000 companies globally with a fleet large enough to have this
problem, at a $30k average, and the reachable market is roughly $60M ARR today —
genuinely small, and growing quickly as fleets scale and learned policies replace
scripted ones. The bet is on the derivative, not the current number, and I'd
rather state that honestly than inflate it with an "AI market" figure.

**Why this gets bigger:** every robot shipped with a learned policy instead of
scripted logic increases both fleet count and per-fleet value. The regulatory
direction — record-keeping and traceability obligations for high-risk autonomous
systems — turns "we couldn't reproduce it" from an engineering embarrassment into
a compliance problem. *(Do not cite specific EU AI Act articles until counsel has
reviewed the claim.)*

### Which category best applies?

Developer tools / infrastructure. Secondary: robotics.

---

## Founders

`[SAGAR — all of this section. Notes on what YC is actually testing:]`

**"Tell us about a time you most successfully hacked some (non-computer) system to
your advantage."** They are testing resourcefulness and comfort operating outside
official channels. A small, true, specific story beats an impressive vague one.

**"The most impressive thing you've built or achieved, other than this startup."**
Concrete and verifiable. Scale, constraint, or difficulty — not job titles.

**"Tell us about things you've built before."** Shipped things with users. Link
them.

**If applying solo:** YC will ask why, and whether you're looking for a
co-founder. Have a real answer. Solo founders do get in; unexamined solo founders
do not.

---

## Demo video script (60 seconds)

Founders on camera, then screen. Do not make a product-marketing video — YC wants
to see you explain it.

| Time | Content |
|------|---------|
| 0:00–0:10 | On camera. "I'm Sagar. Watchpoint tells robotics teams why their robot's AI failed." |
| 0:10–0:25 | The incident. "This AMR stopped mid-aisle. Here are the dashboards — CPU 40%, thermals fine, every ROS 2 node publishing normally. Nothing is wrong, and the robot is stopped." |
| 0:25–0:45 | The reveal. Open the incident in Watchpoint. Confidence collapsing frame over frame, AI-001 firing, the OOD signal at 2.7σ, the actual frame with the shadow. |
| 0:45–0:55 | The fix. Replay the captured inputs against new weights. No false detection. |
| 0:55–1:00 | On camera. "Three days of rosbag scrubbing, or ninety seconds. That's the product." |

Record with the seeded demo. Do not fake a UI you haven't built.

---

## Pre-submission checklist

- [ ] Every `[SAGAR]` placeholder replaced with a true answer
- [ ] Traction answers re-verified on submission day
- [ ] At least 15 robotics engineer conversations completed, with notes
- [ ] Live demo URL working, seeded, and load-tested for a few concurrent viewers
- [ ] Demo video recorded with founders on camera
- [ ] No metric anywhere without evidence behind it (see `positioning.md` §10)
- [ ] Regulatory claims either sourced or removed
- [ ] Repo public, README accurate, license consistent
- [ ] Someone outside robotics has read the 50-character description and understood it

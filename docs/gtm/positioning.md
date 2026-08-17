# Positioning

Canonical source of truth for how Watchpoint is described. Landing page, pricing,
pitch, blog, and outreach all derive from this file. If a claim isn't here, don't
put it on the website.

Last updated: 2026-08-05.

---

## 1. The one-liner

> **AI failure forensics for physical AI.** When your robot fails in the field, we
> tell you why — at the AI layer, not just the logs.

Alternate, for audiences who don't know the term "physical AI":

> **Your logs said the robot was healthy. It still stopped for a shadow.**
> Watchpoint captures what the model saw, predicted, and decided — so you can
> replay the exact failure instead of guessing.

---

## 2. Positioning statement

**For** robotics and edge-AI teams (10–200 engineers) running ROS 2 or custom
autonomy stacks,
**who** lose days per field incident reconstructing why an autonomous system made
a bad decision,
**Watchpoint is** an incident forensics platform for the AI layer
**that** captures model inputs, activations, confidence, decisions, and
out-of-distribution signals at the moment of failure, and replays that exact
inference deterministically.

**Unlike** infrastructure monitoring (Datadog, Grafana, Prometheus) or robotics
visualization (Foxglove, rosbag tooling), which show the model as a black box,
**Watchpoint** opens the box — and correlates the model's internal state with the
system telemetry around it, on one timeline.

---

## 3. The wedge

Every existing tool answers "was the machine healthy?" Almost none answer
**"was the model right, and if not, why?"**

This matters because the two questions diverge exactly when it counts. In the
failure modes that hurt most, **the system metrics look completely normal.** CPU
is fine. Memory is fine. Every ROS 2 node is publishing at its nominal rate. The
robot still did the wrong thing.

Watchpoint captures the four things nothing else in the stack retains:

| # | Layer | What we capture | Why nothing else has it |
|---|-------|-----------------|-------------------------|
| 1 | **What the model saw** | Synced camera frames, lidar, depth, at inference time | rosbags are too big to keep always-on; sampling loses the failure frame |
| 2 | **What the model predicted** | Outputs, per-class confidence, attention/saliency maps | Never leaves the process — no framework exports this by default |
| 3 | **What the policy decided** | Chosen action, the alternatives it ranked, and their scores | Discarded the instant the action is published |
| 4 | **Whether the input was novel** | Embedding distance from the training-set distribution | Requires training-set statistics at inference time on the edge |

**The unlock:** with all four retained, root cause stops being an archaeology
project. You don't infer what the model was thinking from downstream effects —
you read it directly, and you can re-run it.

---

## 4. Ideal customer profile

**Firmographic**

| Attribute | Target |
|-----------|--------|
| Company stage | Seed to Series B robotics / autonomy |
| Engineering size | 10–200 engineers |
| Fleet size | 5–500 units in the field or in pilot |
| Stack | ROS 2 (Humble/Jazzy) or custom C++/Python autonomy |
| Compute | NVIDIA Jetson (Orin/Xavier), x86 industrial PCs |
| Models | Learned perception in production; increasingly learned policy |

**Verticals, in priority order**

1. **Warehouse / intralogistics AMRs** — dense fleets, tolerant of pilots, incidents are frequent and cheap
2. **Agricultural robotics** — brutal visual conditions (dust, glare, mud) make OOD and sensor degradation the daily reality
3. **Last-mile / sidewalk delivery** — high novelty environments, public-safety scrutiny
4. **Inspection drones & industrial** — expensive missions, high cost per failed run

**Deliberately not the first customer:** automotive AV programs. They have
internal tooling teams, multi-year procurement, and safety processes that will
outlast a seed startup's runway. Come back at Series B.

**Buyer vs. user**

- **User:** autonomy engineer / perception engineer — the person who gets paged
- **Champion:** head of autonomy, VP Engineering — owns the "why are we shipping so slowly" problem
- **Blocker:** security / IT — "you want to send our camera data where?" → **this is why the self-hosted wedge exists**

---

## 5. The trigger event

Nobody buys observability on a calm Tuesday. Watchpoint gets bought right after:

- A field incident that took **more than three days** to root-cause
- A **customer-visible failure** with no explanation available for the postmortem
- A **fleet-wide model rollout** that regressed and had to be rolled back blind
- A **safety review or audit** that asked "show me why the system did that" and the team had no answer
- Hiring a new autonomy engineer who asks why debugging is done by watching rosbags by hand

Outreach should reference the trigger, not the product.

---

## 6. Competitive landscape

The honest version. Do not claim these tools are bad — claim they answer a
different question.

| Category | Who | What they do well | The gap we fill |
|----------|-----|-------------------|-----------------|
| **Infra monitoring** | Datadog, Grafana, Prometheus | System health, dashboards, alerting at scale | Model is a black box. "CPU normal" is exactly the misleading signal in AI failures |
| **Robotics visualization** | Foxglove, Rerun, rosbag tooling | Superb sensor/topic visualization and replay | You still have to know what to look for. No model introspection, no automated root cause |
| **ML observability** | Arize, WhyLabs, Fiddler, Evidently | Drift and quality monitoring for deployed models | Built for server-side batch/tabular inference. No hard real-time constraint, no sensor sync, no incident model, no edge deployment |
| **Experiment tracking** | Weights & Biases, MLflow | Training-time lineage and metrics | Stops at deployment. Nothing about what happened in the field |
| **APM / error tracking** | Sentry | Exceptions and stack traces | AI failures throw no exception. The code ran perfectly and returned a wrong answer |
| **Data engines** | Scale Nucleus, Roboflow | Dataset curation and mining | Improve the next model. Don't explain last night's incident |
| **Build it in-house** | Every serious robotics team | Fits their stack exactly | **This is the real competitor.** Costs 1–2 engineers indefinitely and is always the first thing deprioritized |

### What we understand that they don't

1. **In the failures that matter, the infrastructure telemetry is clean.** Tools
   built on the assumption that resource metrics predict failure are structurally
   blind to model-layer faults. This is not a feature gap — it's a modeling
   assumption baked into the product.

2. **Robotics AI failures are physical, not statistical.** ML observability
   assumes drift is gradual and detected over a population. A robot's failure is a
   single 200ms window with a specific frame in it. You need forensics on one
   event, not aggregate distribution monitoring.

3. **The data can't leave the building.** Camera footage from a customer's
   warehouse is often contractually un-exportable. Every SaaS-first ML
   observability vendor hits this wall in robotics. Self-hosted isn't a
   nice-to-have here — it's the only way in the door.

4. **The regression is the deploy.** In robotics, model weights ship like code but
   are debugged like magic. Tying incidents to `weights_hash` is obvious in
   retrospect and almost nobody does it.

---

## 7. Why now

- **Autonomy is shifting from scripted to learned.** End-to-end and VLA policies
  mean the decision itself is now a model output, not `if` statements an engineer
  can read. The debugging tools have not followed.
- **Fleets crossed the manual-triage threshold.** At 5 robots you watch the
  rosbag. At 100 you cannot, and most teams are crossing that line now.
- **Regulation is arriving with record-keeping teeth.** The EU AI Act's
  requirements for high-risk systems include automatic logging and traceability
  over the system's lifetime; safety-case frameworks like UL 4600 expect evidence,
  not assurances. "We couldn't reproduce it" is becoming a compliance problem, not
  just an engineering one. *(Cite specific articles only after legal review —
  see §10.)*
- **Edge compute finally has headroom.** An Orin has the budget to spare for
  sub-1% introspection overhead. On a Jetson Nano five years ago it did not.

---

## 8. Messaging pillars

Every asset should hit at least two of these three.

**Pillar 1 — See what the model saw.**
Not a proxy. Not a downstream symptom. The actual frame, the actual activations,
the actual confidence vector, at the timestamp of the failure.
*Proof:* attention overlay on the incident frame.

**Pillar 2 — Root cause, not a dashboard.**
Watchpoint names the failure — `AI-001: perception confidence collapse` — instead
of handing you eleven charts and wishing you luck.
*Proof:* the AI-001…AI-008 rule taxonomy, plus the classic 7-rule system engine.

**Pillar 3 — Your data never leaves your VPC.**
Self-hosted by default, Apache-2.0 core. The security review that kills other
vendors is the one we're built for.
*Proof:* `docker compose up`, no outbound dependency, LLM summaries degrade
gracefully to rules text with no API key.

---

## 9. Objection handling

| Objection | Response |
|-----------|----------|
| "We already have Grafana / Datadog." | Keep it. Those tell you the machine was healthy. Watchpoint tells you why a healthy machine made the wrong decision. Most of our failure modes fire while every infra metric is nominal. |
| "We just look at rosbags." | Until you can't. Rosbags don't retain model internals at all, and always-on recording at fleet scale is unaffordable. We ring-buffer and flush only on incident. |
| "Overhead on our robot?" | Design budget is <1% at p99, ring-buffered in-process, zero-copy where possible, and nothing is transmitted until an incident triggers. Measure it yourself — the collector is open source. |
| "We can't send camera data to a vendor." | You don't. Self-hosted in your VPC is the default deployment. Hosted cloud is opt-in and later. |
| "We'd build this ourselves." | You could — teams do. It's typically 1–2 engineers of sustained work, and it's the first thing cut when a customer deadline hits. The taxonomy is the hard part, not the plumbing. |
| "Our models are proprietary." | We never need weights to leave your infrastructure. We hash them for lineage; we don't upload them. |
| "You're pre-revenue and tiny." | True. That's the design-partner offer: free for 12 months, and we build your top failure mode into the rules engine ourselves. |

---

## 10. Claim discipline

The website is a public artifact of a company that is asking people for money and
data. Two hard rules:

**Never state a metric we cannot produce evidence for.** No invented customer
counts, incident volumes, MTTR reductions, or logos. If we haven't measured it,
it doesn't ship. Aspirational numbers on a landing page are the fastest way to
fail a diligence conversation, and a robotics buyer will ask for the methodology.

**Label the roadmap as roadmap.** Replay sandbox, Grad-CAM endpoint, rules
AI-004…AI-008, and hosted cloud are not built yet. They are marked as such
everywhere they appear. Shipped means merged, tested, and demoable.

Regulatory claims (EU AI Act, ISO 26262, UL 4600) get reviewed by counsel before
any specific article or clause number appears in customer-facing copy. Until
then, describe the trend, not the citation.

---

## 11. Naming and voice

- **Watchpoint**, one word, capital W. Never "WatchPoint" or "Watch Point".
- Rule IDs are uppercase with a hyphen: `AI-001`, not `ai001`.
- Voice: engineer to engineer. Specific over sweeping. A named failure mode beats
  an adjective every time.
- Avoid: "revolutionary", "cutting-edge", "AI-powered", "seamless", "unlock the
  power of". Robotics engineers have a very short fuse for this register.
- Prefer concrete nouns: shadow, fog, confidence, frame, weights hash, 200ms.

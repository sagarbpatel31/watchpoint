# Design partner playbook

How Watchpoint gets its first five users. Last updated: 2026-08-05.

**The goal is not five logos. It is five teams who would be genuinely annoyed if
you turned it off.** Everything below optimises for that, which means
disqualifying fast is as valuable as closing.

---

## 1. The offer

> Free for 12 months. We build your failure mode.

**They get**

- Team tier at no cost for 12 months, self-hosted in their infrastructure
- The failure mode costing their team the most time, implemented as a first-class
  rule in the engine — built by us, not filed as a feature request
- Direct access to the founder, not a support queue
- Influence over the roadmap while it's still cheap to change

**We get**

- An hour every two weeks, on a call, with an engineer who actually uses it
- Honest feedback, including "we stopped using it and here's why"
- Permission to reference them publicly **once they're happy** — never as a
  condition of the deal
- Anonymised failure patterns to sharpen the taxonomy

**We do not get, and must never ask for:** their data, their weights, or their
footage. The entire product is self-hosted. If a conversation drifts toward
"could you send us a sample dataset," you have broken the promise that got you in
the door.

### Why free rather than discounted

At this stage you are buying information, not revenue. A paying customer at $500
generates pricing anxiety and no useful signal. A design partner who gets real
value for free will tell you the truth, and converts at renewal on the merits.
Charge when the product is boring and reliable, not while you're learning what it
is.

---

## 2. Who qualifies

**Must have all four:**

| Criterion | Why it's non-negotiable |
|-----------|-------------------------|
| 5+ robots deployed outside the lab | Below 5, one engineer still holds the whole fleet in their head and the pain isn't real yet |
| Learned perception in production today | Not "planning to add ML." Without a live model there's nothing for the collector to hook |
| Lost >1 day to a field incident recently | This is the trigger. No recent pain, no urgency, no engagement |
| Can self-host Postgres and a container | If they need a managed offering, they're a future customer, not a design partner |

**Strong positive signals**

- ROS 2 (Humble or Jazzy) — best-supported path
- NVIDIA Jetson Orin / Xavier fleet
- An engineer whose job description includes "field debugging" or "fleet reliability"
- They've started building something like this internally and stalled
- Recently shipped a model update that regressed and got rolled back

**Disqualify immediately — say so kindly and move on**

- Automotive AV programmes. Internal tooling teams, multi-year procurement, safety
  processes that outlast your runway. Revisit at Series B.
- Pre-deployment startups. No fleet, no incidents, no signal.
- Anyone whose first question is about pricing tiers. That's a buyer evaluating a
  mature product, not a partner co-building one.
- Anyone who wants a managed cloud offering. It doesn't exist and won't for a while.
- Research labs without a deployed fleet. Fascinating conversations, zero product signal.

### Target verticals, in priority order

1. **Warehouse / intralogistics AMRs** — dense fleets, pilot-friendly, incidents frequent and low-stakes
2. **Agricultural robotics** — dust, glare, and mud make OOD and sensor degradation a daily reality
3. **Last-mile / sidewalk delivery** — high environmental novelty, public scrutiny
4. **Inspection drones and industrial** — high cost per failed mission

---

## 3. Building the list

Target **40 qualified companies**. At realistic conversion that's ~12 conversations
and ~5 partners.

**Where they are**

- ROS Discourse — read who posts about field debugging and fleet reliability
- ROSCon talks from the last two years, especially anything about deployment or
  reliability. Speakers are self-identifying as having this problem in public.
- GitHub — contributors to `ros2`, `nav2`, `micro-ROS`, and issue threads about
  field failures
- Job postings for "robotics data infrastructure", "fleet reliability engineer",
  "robot data platform" — a company hiring for this has budgeted for the pain
- Robotics newsletters and their portfolio pages: The Robot Report, Robot Talk,
  investor portfolios (Eclipse, Lux, Playground)
- ROSCon, ICRA, IROS attendee and sponsor lists

**Qualify before writing.** Fifteen minutes per company: do they have a deployed
fleet, what's the stack, who's the right engineer, is there a recent public
incident or postmortem you can reference? A generic email to an unqualified company
is worse than no email — it burns the name.

**Track it.** A spreadsheet is fine. Columns: company, vertical, fleet size, stack,
contact, source, trigger event, outreach date, response, call date, outcome,
notes. Fifteen minutes of hygiene a week beats any CRM at this stage.

---

## 4. Outreach

Rules that matter more than the templates:

- **Reference the trigger, not the product.** Nobody wakes up wanting observability.
- **Ask for a conversation, not a demo.** You're learning; act like it.
- **Never send a deck first.** The repo is more credible than any slide.
- **Under 150 words.** Engineers read email on a phone between standups.
- **One follow-up, then stop.** Two is diligence, three is spam and it costs you the name permanently.

### Template A — cold, engineer-to-engineer

> **Subject:** how do you debug a bad detection in the field?
>
> Hi {name},
>
> I saw your {ROSCon talk / post on ROS Discourse / nav2 issue} about {specific
> thing}. Quick question, because I'm trying to find out whether this is universal
> or just my old team:
>
> When one of your robots does something wrong in the field and the system metrics
> all look normal — CPU fine, topics publishing, no exceptions — how do you
> currently find out what the model actually saw and why it decided that?
>
> I'm building tooling for exactly this problem (Apache 2.0, self-hosted:
> {repo link}) and I'd rather hear how you handle it today than pitch you.
>
> 20 minutes in the next couple of weeks?
>
> {signature}

### Template B — warm, after a public incident or postmortem

> **Subject:** your {incident} writeup
>
> Hi {name},
>
> Read your writeup on {incident}. The part about {specific detail} matched
> something I've been chasing: the dashboards stay green the whole time because
> the machine genuinely is healthy — it's the model that's wrong.
>
> I'm building a tool that captures what the model saw, predicted, and decided at
> failure time so that's a lookup instead of a rosbag archaeology session. Free for
> a year for design partners, and I'll build your worst failure mode into the rules
> engine myself.
>
> Worth 20 minutes? Happy to just compare notes if not.
>
> {signature}

### Template C — the one follow-up

> **Subject:** re: how do you debug a bad detection in the field?
>
> Hi {name} — following up once in case this got buried.
>
> If it's not a problem you have, tell me and I'll stop. That's genuinely useful
> data for me either way.
>
> {signature}

That last line converts better than any amount of persistence, and it keeps the
relationship clean when the answer is no.

---

## 5. The discovery call

**30 minutes. Talk for less than a third of it.**

The failure mode is demoing too early. If you demo in the first ten minutes,
you've traded the only thing you needed — an unbiased description of their
process — for a reaction to your UI.

**Open (2 min).** "I'm trying to understand how teams debug AI failures in the
field. I'll demo at the end if it's relevant, but I mostly want to hear how you
work today."

**Their world (10 min).** Fleet size, environments, stack, models, who gets paged.

**The incident (10 min).** *This is the whole call.* "Tell me about the last time a
robot did something wrong and you couldn't immediately explain it."

Then push for specifics — the difference between a useful call and a pleasant one:

- How long from failure to root cause? *(Get a number. "A while" is not data.)*
- Walk me through what you actually did, step by step.
- What did you look at first? What did that tell you?
- What did you wish you had and didn't?
- How did you finally figure it out?
- **Did you ever actually figure it out?** *(Notice how often the answer is no.)*
- How many of these happen a month?
- Who else got pulled in? For how long?

**Only then, demo (5 min).** Show the **confidence collapse** (AI-001). That is
the rule that runs on genuinely captured model state, so it is the one you can
show without caveat.

Do **not** lead with the OOD signal. AI-002 is merged, but nothing produces
`OODSignal` rows outside the demo seed, so what you would be pointing at is
illustrative data. If it comes up, say so in those words — see below.

**Close (3 min).** "Would you want to try this on your fleet?" Then shut up.

### When they ask "is this actually running on real robots?"

They will, and it is the right question. The honest answer is a stronger
position than a hedge — these are engineers, they will find the seam in the
demo within a week of installing, and being told up front is what earns the
second conversation.

What is true today, in plain terms:

- The collectors capture real data: host metrics from `/proc`, ROS 2 topic and
  node health, and per-inference outputs, per-class confidence and output
  statistics from PyTorch forward hooks.
- **One** AI rule runs on that captured data end to end — confidence collapse
  (AI-001) — alongside seven system-level rules that run on real host and ROS 2
  telemetry.
- AI-003 reads inference latency, which the collector does not populate yet, so
  it currently fires only against the seed.
- Out-of-distribution scoring, attention overlays, and deterministic replay are
  **built into the plan, not into the product.** The demo shows them with
  seeded data so you can see the shape of the thing.
- It has not yet run on a production robot fleet. That is exactly what a design
  partnership is for.

Say the last point without flinching. "You would be the first" is a real offer
to a team that wants influence over the roadmap, and a wasted meeting with a
team that wants a finished product — and you want to find out which they are on
call one, not in month three.

### Reading the answer

| Signal | Meaning |
|--------|---------|
| "How would we get it on our robots?" | Real interest. Move to next steps now. |
| "Can you also do X?" | Real interest, and X might be their rule. Dig. |
| "Let me talk to the team" | Soft no most of the time. Ask what specifically they'd need to bring back. |
| "Send me some info" | No. Send it anyway, don't chase. |
| "We built something like this internally" | **Best signal in the set.** They've validated the problem with their own budget. Ask what theirs doesn't do. |

### The number that matters

Track **time-to-root-cause, before and after.** If a partner's median goes from
three days to two hours, that's the case study, the pricing justification, and the
YC traction answer, all from one metric. Ask for the baseline on the first call,
before they've used anything — you cannot reconstruct it later.

---

## 6. Onboarding

Aim for **first captured inference within one week** of yes. Momentum dies in
setup friction.

| Day | What happens | Owner |
|-----|--------------|-------|
| 0 | Yes. Send the agreement (§7) and a shared channel invite. | You |
| 1 | 60-min technical call: their stack, where the collector attaches, what triggers an incident. | Both |
| 2–3 | They stand up the stack; you're in the channel answering in minutes, not hours. | Them |
| 4–5 | Attach hooks to one model on one robot. Not the fleet. One. | Both |
| 7 | First real captured inference. Screenshot it. That's the moment it becomes real. | Both |
| 14 | First check-in. Has anything fired? Was it right? Any false positives? | Both |
| 30 | Their custom rule specified and scheduled. | You |

**Blockers to pre-empt, because they will all happen:**

- Ingest endpoints are currently unauthenticated. **Do not put a partner's fleet on
  a network-exposed instance until device tokens ship.** VPN or private network
  only, and say this out loud rather than hoping they don't look.
- The Go edge agent still simulates some host metrics — be upfront, or they'll
  find it and lose trust in everything else.
- ONNX and TensorRT adapters aren't built. PyTorch only. Confirm the framework on
  the first call, before saying yes.

Honesty about gaps is not a weakness in this motion. A partner who discovers a
limitation you hid stops believing your other claims immediately.

---

## 7. Design partner agreement

Keep it to one page. A 12-page contract signals you don't understand your own
stage. **Have a lawyer review before sending the first one** — the terms below are
a starting structure, not legal advice.

**Term** — 12 months from first deployment.

**What we provide**
1. Team-tier features, free, self-hosted, for the term
2. One custom rule implemented for their top failure mode, scoped jointly within 30 days
3. Founder-direct support, one business day response
4. 30 days' notice before any change that would break their deployment

**What they provide**
1. A biweekly 60-minute call for the term
2. Honest feedback, including negative
3. Deployment on at least one production robot within 30 days

**Data** — Watchpoint is self-hosted. We receive no telemetry, footage, or model
weights. Any diagnostic data shared is explicitly shared, case by case, by them.

**Publicity** — neither party names the other publicly without written consent.
Consent is asked for after they're happy, never as a condition.

**IP** — they own their data and models. We own the platform. Rules built during
the partnership ship to all users, including the free tier. *(Say this explicitly
up front — a partner who assumed exclusivity and discovers otherwise is a
reference lost.)*

**Exit** — either party may end it with 30 days' notice, no penalty. Self-hosted
means their data never moves.

**After the term** — Community tier free forever, or Team at a founding-partner
rate locked for 24 months.

---

## 8. What good looks like

**By 30 days:** 40 companies qualified, 20 contacted, 5+ calls booked.

**By 60 days:** 3 partners deployed, one captured inference from a real robot,
one baseline time-to-root-cause number recorded.

**By 90 days:** 5 partners, 2 custom rules shipped, and — the actual bar — **one
incident a partner solved with Watchpoint that they could not have solved
otherwise.** One of those is worth more than fifty signups.

### Signals you're wrong about something

Take these seriously rather than pushing harder:

- **High interest, no deployments** → the value is understood but setup cost exceeds
  perceived benefit. Fix onboarding, not the pitch.
- **Deployments, no engagement** → it's a curiosity, not a tool. The rules aren't
  firing on anything they care about.
- **"We built this internally" from >50%** → the problem is real and the wedge may
  be too narrow. Go deeper on what theirs can't do.
- **Nobody can name a recent incident** → you've mis-qualified the segment. Their
  fleets are too small or too scripted.
- **Everyone asks for hosted** → self-hosted-first was wrong for this segment.
  That's a strategy update, not an objection to overcome.

---

## Appendix — contact hygiene

The pricing page and this playbook currently route to a personal Gmail address,
which is fine for the first ten conversations and not fine on a public page long
term. Before any real outreach volume:

1. Register the domain and set up `sagar@` and `hello@`
2. Update `CONTACT_EMAIL` in `apps/web/src/app/pricing/page.tsx`
3. Set up SPF/DKIM/DMARC before cold outreach — a fresh domain without them lands
   in spam, and you'll conclude the message failed when the delivery did
4. Warm the domain for two weeks at low volume before sending at any scale

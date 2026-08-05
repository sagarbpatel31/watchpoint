---
title: "8 ways your robot's AI fails silently"
description: "Your dashboards are green and the robot is still wrong. A field guide to the failure modes that live below the logs."
author: Sagar Patel
date: 2026-08-05
status: draft
canonical: https://watchpoint.ai/blog/eight-silent-ai-failures
---

# 8 ways your robot's AI fails silently

An AMR stops mid-aisle and won't proceed. You open the dashboards.

CPU: 40%. Memory: flat. Thermals: nominal. Every ROS 2 node publishing at its
expected rate. No exceptions, no core dumps, no OOM killer. Every monitor you have
is green.

The robot is still stopped.

Eventually someone pulls the rosbag and scrubs through it frame by frame until
they find it: a hard shadow across the loading bay that the detector called an
obstacle at 0.71 confidence. Three days, to find one frame.

This is the characteristic shape of an AI failure in a physical system. **The
machine is perfectly healthy and the model is wrong.** Every tool in a standard
robotics stack is built on the opposite assumption — that resource health predicts
system health — which is exactly why they all report green while the robot sits
there.

Below are eight failure modes we keep seeing, why the usual instrumentation
misses each one, and what you'd need to capture to catch it. They map to the rule
IDs in [Watchpoint](https://github.com/sagarbpatel31/watchpoint), which is
Apache-2.0 and self-hosted, so you can go read the detectors rather than take my
word for the thresholds.

---

## Why logs structurally can't see this

Worth being precise about the root cause, because it explains all eight.

A log line is something a human decided in advance was worth writing down. An
exception is a code path that failed. Neither happens here: the perception stack
ran correctly, in the expected time, and returned a well-formed answer that
happened to be wrong.

Meanwhile the state that would explain the wrongness — the input tensor, the
activations, the confidence vector, the ranked alternatives the policy
considered — lives in process memory for a few milliseconds and is then
overwritten by the next frame. Nothing in the standard stack retains it, because
retaining all of it always is unaffordable at fleet scale.

So the evidence is destroyed at ~30Hz, and you are left reconstructing the
model's reasoning from downstream side effects. That is the actual job everyone is
doing by hand, and it's why it takes days.

---

## AI-001 — Perception confidence collapse

**In the field:** detection quality degrades over minutes to hours rather than
failing outright. The robot gets tentative — more stops, more re-planning, more
"why is it driving like that" from the operations team. Nothing errors.

**Why you miss it:** confidence is an internal model output. It goes into a
threshold comparison and is discarded. Nobody trends it, so a slide from 0.93 to
0.44 is invisible unless someone happens to be watching the right topic at the
right moment.

**How to detect it:** trend the median confidence across the incident window and
compare halves. Watchpoint's AI-001 splits the window at the midpoint, takes the
median of each half, and fires when the drop exceeds 30% — requiring at least 6
frames so sparse data doesn't produce noise. Median rather than mean matters
here: a handful of confident detections shouldn't mask a collapsing floor.

**The tell that makes it worth catching:** confidence usually starts sliding well
before the robot visibly misbehaves. It's one of the few genuinely leading
indicators available at the model layer.

> `AI-001` · severity high · **shipped**

---

## AI-002 — Out-of-distribution input

**In the field:** the robot encounters something the training set never contained
— a pallet wrapped in mirror-finish film, low winter sun straight into the
camera, a floor that was repainted last weekend — and the model produces a
confident, wrong answer.

**Why you miss it:** this is the dangerous one, because **confidence does not drop
when it should.** A model asked to classify something outside its distribution
frequently returns high confidence for the nearest class it knows. There is no
signal anywhere in the system that the input was novel, because novelty is a
property of the input's relationship to the training data — and the training data
isn't on the robot.

**How to detect it:** extract a penultimate-layer embedding at inference time and
measure its distance from the training-set centroid, in σ. Push the training-set
statistics to the edge at deploy time; you're comparing against a summary, not
the dataset. Watchpoint's AI-002 fires on any OOD signal linked to an incident and
scales its own confidence with how many fired.

**The uncomfortable implication:** if you aren't measuring OOD, you have no way to
distinguish "the model knows this" from "the model has never seen this and is
guessing confidently." Those are opposite situations that look identical from
outside the process.

> `AI-002` · severity medium · **shipped**

---

## AI-003 — Inference latency spike

**In the field:** the control loop starts missing deadlines. The robot's motion
gets jerky, obstacle response degrades, and a watchdog eventually trips. The model
is still producing correct answers — just too late to be useful.

**Why you miss it:** this one your infra monitoring *can* see, and it's on the
list precisely because the correlation is what matters. You'll observe GPU
utilisation climbing and, separately, mission aborts, without the link between
them. The connection is per-inference latency, which lives between the two and is
usually measured by nobody.

**How to detect it:** track p99, not mean — the mean stays comfortable while the
tail eats your deadlines. Watchpoint's AI-003 compares the p99 of each half of the
incident window and fires at a 2× increase. Common causes: thermal throttling,
CPU contention from a co-located process, memory pressure forcing recompute.

**Note on the boring failure mode:** a huge share of "the AI is broken" incidents
are actually "someone deployed a second model to the same Jetson." Latency
correlation finds these in minutes.

> `AI-003` · severity medium · **shipped**

---

## AI-004 — Per-layer latency anomaly

**In the field:** total inference time creeps up 3–4× with no change in input
resolution, batch size, or hardware, usually after an "unrelated" dependency
bump.

**Why you miss it:** end-to-end latency is one number. It tells you the model got
slower, not which part. The usual response is to profile locally, where the
problem does not reproduce, because the cause is on the device.

**How to detect it:** capture per-layer timings from the runtime and baseline
each layer independently. When one layer moves 5× while everything else stays
flat, you have a specific answer: a TensorRT engine that silently fell back to a
slower kernel, an unfused operation after a version change, a layout conversion
inserted between two ops. Most valuable on TensorRT, where kernel selection is
opaque and version-sensitive.

> `AI-004` · severity low · *specified, not yet merged*

---

## AI-005 — Decision–perception mismatch

**In the field:** the worst category, and the one that ends up in incident
reviews. Perception was **right**. The pedestrian was detected at 0.96 confidence,
correctly classified, correctly tracked. The policy chose to continue anyway.

**Why you miss it:** every component reports success. The detector logs a
detection. The planner logs a valid plan. The controller logs successful
execution. Each subsystem did its job; the failure lives in the *seam* between
perception output and policy input — a misweighted cost term, a stale config, a
confidence threshold that disagrees with the one perception is using.

**How to detect it:** you have to capture the decision, not just the action. What
did the policy choose, what were the alternatives, and how were they scored? With
the ranked alternatives retained, "reroute was considered and scored 0.31 against
continue at 0.34" turns an unanswerable question into a config diff. Without them,
you are guessing at the contents of a function that already returned.

**Why this one justifies the whole approach:** no amount of system telemetry will
ever surface it. Every metric is nominal, every component is healthy, and the
robot did something indefensible.

> `AI-005` · severity high · *specified, not yet merged*

---

## AI-006 — Attention drift

**In the field:** the model is still right, but for the wrong reason. Accuracy
holds in testing and collapses on a new site, a new lighting rig, or a repainted
floor.

**Why you miss it:** accuracy metrics cannot distinguish a correct answer from a
correct answer derived from a spurious feature. A detector that has learned to
find forklifts by the yellow floor markings near them scores perfectly — until
someone repaints the warehouse.

**How to detect it:** compute the center-of-mass of the saliency or attention map
(Grad-CAM for CNNs, attention rollout for ViTs) and baseline it. A shift greater
than 50% of the frame while predictions stay stable means the model changed what
it's looking at without changing what it says. That's a regression that hasn't
surfaced yet.

**Why it's rated low severity but matters:** it rarely causes today's incident. It
reliably predicts next quarter's, at the new site.

> `AI-006` · severity low · *specified, not yet merged*

---

## AI-007 — Output saturation

**In the field:** the model returns 0.99 for everything. Every frame is maximally
confident, including the ambiguous ones, including the ones it gets wrong.
Downstream logic that gates on confidence thresholds stops gating on anything.

**Why you miss it:** high confidence reads as health on every dashboard anyone
builds. A saturated model looks *better* than a healthy one by every metric you're
likely to be plotting.

**How to detect it:** measure the entropy of the output distribution across
diverse inputs. A well-calibrated model is uncertain about genuinely ambiguous
inputs; entropy below ~0.1 nats across a varied input stream means calibration is
gone. Usual culprits: a quantisation step that crushed the output range, a
temperature parameter lost in an export, training that ran too long on too little
data.

**The practical consequence:** every confidence threshold in your stack is now
dead code. Anything downstream that reads `if confidence > 0.8` is unconditionally
true, and you won't find that by reading the code.

> `AI-007` · severity medium · *specified, not yet merged*

---

## AI-008 — Sensor degradation upstream of the model

**In the field:** condensation on a lens over twenty minutes. Dust on a lidar
after an afternoon in a field. A camera knocked 3° out of alignment by a docking
bump. Detection quality decays smoothly, and no threshold is ever crossed.

**Why you miss it:** the camera is working. It publishes at 30Hz, the frames are
well-formed, the driver reports no errors, and every health check passes. The
*information content* of those frames is collapsing, which nothing measures.

**How to detect it:** compute cheap input-quality statistics per frame — Laplacian
variance for sharpness, brightness histogram spread, lidar points-per-cubic-metre
— and baseline them. A 40% drop in sharpness with the topic still at nominal rate
is a fogged lens, findable in seconds instead of by process of elimination.

**Why it pairs with AI-001:** they fire together and the pair is the diagnosis. On
its own, a confidence drop tells you the model is struggling. Together with a
sharpness drop, you know *why*, and the fix is a cloth rather than a retraining
run. That's the difference between a twenty-minute incident and a two-week one.

> `AI-008` · severity medium · *specified, not yet merged*

---

## The pattern

Read the eight together and the same structure appears every time:

1. **The evidence lives inside the process** and is overwritten within
   milliseconds.
2. **Every component reports success**, because every component succeeded.
3. **Infra telemetry is clean**, because the machine genuinely is healthy.
4. **The failure is in the model's judgement**, and judgement isn't a metric
   anyone is currently collecting.

Which means no amount of additional system monitoring will find these. You could
add a hundred more Grafana panels and catch none of the eight. The missing
capability isn't more telemetry — it's *retaining different telemetry*: the
model's own state at the moment it was wrong.

That's a tractable engineering problem. Ring-buffer the model's inputs, outputs,
confidence, and decisions in-process; keep it bounded so the overhead stays under
1%; flush only when an incident triggers so you're not paying to store 30Hz of
nothing. Then the question "why did the robot do that?" has an answer you can
look up instead of reconstruct.

---

## Try it

Watchpoint implements this. It's Apache 2.0, self-hosted, and the whole stack runs
locally:

```bash
git clone https://github.com/sagarbpatel31/watchpoint.git
cd watchpoint/deploy/docker-compose && docker compose up -d
curl -X POST localhost:8000/api/v1/seed/demo
```

That seeds three incidents carrying both system telemetry and captured AI-layer
inferences, including a confidence collapse with an OOD signal at 2.7σ.

AI-001, AI-002, and AI-003 are merged and running today. AI-004 through AI-008 are
specified and on the roadmap — I'd rather tell you which is which than let you
find out after installing.

**If you're running a fleet and any of these eight look familiar, I'd like to talk
to you.** I'm taking on a small number of design partners: free for a year, and I
build the failure mode that's costing your team the most time into the rules
engine myself. Reply, or open an issue on the repo.

---

*Corrections and disagreement welcome — particularly if you think one of the eight
is wrong, or if you've hit a ninth. The taxonomy is only useful if it matches what
actually happens to real fleets.*

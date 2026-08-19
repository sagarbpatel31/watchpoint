import Link from "next/link";
import {
  Activity,
  ArrowRight,
  Boxes,
  Brain,
  Camera,
  Crosshair,
  Eye,
  GitBranch,
  Layers,
  Lock,
  Radio,
  RefreshCw,
  Server,
  ShieldCheck,
  Workflow,
} from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const REPO_URL = "https://github.com/sagarbpatel31/watchpoint";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Nav */}
      <nav className="border-b border-border/40 backdrop-blur-sm sticky top-0 z-50 bg-background/80">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
              <Activity className="w-5 h-5 text-primary-foreground" />
            </div>
            <span className="text-lg font-bold tracking-tight">Watchpoint</span>
          </div>
          <div className="flex items-center gap-5">
            <a
              href="#failures"
              className="hidden sm:inline text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Failure modes
            </a>
            <Link
              href="/pricing"
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Pricing
            </Link>
            <a
              href={REPO_URL}
              className="hidden sm:inline text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              GitHub
            </a>
            <Link href="/dashboard" className={cn(buttonVariants({ size: "sm" }))}>
              View Demo
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="py-24 md:py-32">
        <div className="max-w-6xl mx-auto px-6">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-border/60 text-xs text-muted-foreground mb-6">
              <Radio className="w-3 h-3 text-green-500 animate-pulse" />
              Apache 2.0 · self-hosted · ROS 2 and custom edge stacks
            </div>
            <h1 className="text-4xl md:text-6xl font-bold tracking-tight leading-[1.1] mb-6">
              Your logs said the
              <br />
              robot was healthy.
              <br />
              <span className="text-muted-foreground">
                It stopped for a shadow.
              </span>
            </h1>
            <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mb-6 leading-relaxed">
              Watchpoint is AI failure forensics for physical AI. It captures what
              your model predicted at the moment of failure — outputs, per-class
              confidence, output statistics — joins it to system and ROS 2
              telemetry on one timeline, and names the failure mode. Root cause at
              the AI layer, not just the logs.
            </p>
            <p className="text-sm text-muted-foreground/80 max-w-2xl mb-8 leading-relaxed">
              Where this is going: deterministic replay of the captured inference
              against new weights, attention overlays on the failure frame, and
              out-of-distribution scoring from live embeddings. None of those
              three work yet, and they are marked as such below — nothing on this
              page claims to run that doesn&apos;t.
            </p>
            <div className="flex flex-wrap gap-4">
              <Link href="/dashboard" className={cn(buttonVariants({ size: "lg" }), "gap-2")}>
                Explore the demo
                <ArrowRight className="w-4 h-4" />
              </Link>
              <a
                href="#quickstart"
                className={cn(buttonVariants({ variant: "outline", size: "lg" }), "gap-2")}
              >
                Run it locally
              </a>
            </div>
            <p className="text-xs text-muted-foreground mt-6">
              No signup for the demo. Self-hosted install runs entirely on your
              own infrastructure.
            </p>
          </div>
        </div>
      </section>

      {/* The four layers — what we capture */}
      <section className="border-y border-border/40 bg-card/20">
        <div className="max-w-6xl mx-auto px-6 py-12">
          <p className="text-sm text-muted-foreground mb-2">
            Four things your stack throws away every frame — and needs at 2am:
          </p>
          <p className="text-xs text-muted-foreground/70 mb-8 max-w-2xl leading-relaxed">
            This is the thesis the product is built around. One of the four is
            captured today; the line under each says exactly where it stands, so
            you can tell the plan from the product.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
            <CaptureLayer
              icon={<Camera className="w-4 h-4" />}
              index="01"
              title="What the model saw"
              detail="Synced camera, lidar, and depth frames at inference time"
              captured="Not captured yet — the ROS 2 sensor ring buffer is unbuilt."
            />
            <CaptureLayer
              icon={<Eye className="w-4 h-4" />}
              index="02"
              title="What it predicted"
              detail="Outputs, per-class confidence, attention and saliency"
              captured="Outputs, per-class confidence and output statistics captured today via the PyTorch hooks. Attention and saliency are not."
            />
            <CaptureLayer
              icon={<Workflow className="w-4 h-4" />}
              index="03"
              title="What the policy decided"
              detail="Chosen action, ranked alternatives, and their scores"
              captured="Schema and ingest endpoint exist; no collector emits decisions yet."
            />
            <CaptureLayer
              icon={<Crosshair className="w-4 h-4" />}
              index="04"
              title="Whether the input was novel"
              detail="Embedding distance from your training distribution"
              captured="Not captured yet — penultimate-layer embedding extraction is unbuilt."
            />
          </div>
        </div>
      </section>

      {/* The problem */}
      <section className="py-24">
        <div className="max-w-6xl mx-auto px-6">
          <div className="grid lg:grid-cols-2 gap-16 items-start">
            <div>
              <h2 className="text-3xl font-bold mb-6 leading-tight">
                The metrics are green.
                <br />
                That&apos;s the whole problem.
              </h2>
              <div className="space-y-4 text-muted-foreground leading-relaxed">
                <p>
                  An AMR halts mid-aisle. You open the dashboards. CPU is at 40%.
                  Memory is flat. Thermals are nominal. Every ROS 2 node is
                  publishing at its nominal rate. Nothing threw an exception.
                </p>
                <p>
                  So you pull the rosbag, scrub through it by hand, and eventually
                  find the frame — a hard shadow across a loading bay that the
                  detector called an obstacle at 0.71 confidence. Three days gone.
                </p>
                <p className="text-foreground">
                  Infrastructure monitoring is structurally blind to this. It is
                  built on the assumption that resource health predicts failure.
                  At the AI layer that assumption is exactly inverted: the
                  machine is perfectly healthy, and the model is wrong.
                </p>
              </div>
            </div>

            <div className="space-y-4">
              <ContrastRow
                label="Datadog, Grafana, Prometheus"
                answers="Was the machine healthy?"
                verdict="Green. Unhelpfully."
              />
              <ContrastRow
                label="Foxglove, rosbag tooling"
                answers="What did the sensors publish?"
                verdict="Everything, if you know what to look for."
              />
              <ContrastRow
                label="Sentry and APM"
                answers="Did the code throw?"
                verdict="No. It ran perfectly and returned a wrong answer."
              />
              <ContrastRow
                label="Watchpoint"
                answers="Was the model right — and if not, why?"
                verdict="AI-001: detection confidence collapsed 0.93 → 0.41."
                highlight
              />
            </div>
          </div>
        </div>
      </section>

      {/* Failure taxonomy */}
      <section id="failures" className="py-24 border-t border-border/40">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold mb-4">
              Eight ways an AI system fails silently
            </h2>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              Watchpoint names the failure instead of handing you eleven charts.
              These rules read model state, not just system telemetry — and each
              one is labelled with how far along it actually is.
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            <RuleCard
              id="AI-001"
              name="Perception confidence collapse"
              trigger="Detection confidence p50 over 60s drops more than 30% from baseline"
              severity="high"
              status="live"
            />
            <RuleCard
              id="AI-002"
              name="Out-of-distribution input"
              trigger="Embedding distance exceeds 3σ from the training-set centroid"
              severity="medium"
              status="demo"
            />
            <RuleCard
              id="AI-003"
              name="Inference latency spike"
              trigger="p99 latency over 60s exceeds 2x baseline"
              severity="medium"
              status="demo"
            />
            <RuleCard
              id="AI-004"
              name="Per-layer latency anomaly"
              trigger="A single layer exceeds 5x its baseline latency"
              severity="low"
            />
            <RuleCard
              id="AI-005"
              name="Decision-perception mismatch"
              trigger="Policy chose an action incompatible with a high-confidence detection"
              severity="high"
              status="demo"
            />
            <RuleCard
              id="AI-006"
              name="Attention drift"
              trigger="Attention center-of-mass shifted more than 50% of frame from baseline"
              severity="low"
            />
            <RuleCard
              id="AI-007"
              name="Output saturation"
              trigger="Softmax entropy below 0.1 nats across diverse inputs"
              severity="medium"
            />
            <RuleCard
              id="AI-008"
              name="Sensor degradation upstream of model"
              trigger="Image sharpness or lidar density dropped more than 40% from baseline"
              severity="medium"
            />
          </div>

          <p className="text-xs text-muted-foreground mt-6 text-center max-w-2xl mx-auto leading-relaxed">
            <span className="text-green-500">live</span> means the rule runs on
            data our collectors actually capture from a running system.{" "}
            <span className="text-amber-500">demo data only</span> means the rule
            is merged but nothing produces its input yet, so it fires against the
            seeded demo and not against your fleet. Unmarked rules are specified
            and on the roadmap. We would rather label the gap than let you find
            it after installing.
          </p>
        </div>
      </section>

      {/* How it works */}
      <section className="py-24 border-t border-border/40">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold mb-4">How it works</h2>
            <p className="text-muted-foreground max-w-xl mx-auto">
              Instrument once, capture continuously in memory, keep only what
              matters.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <StepBlock
              step="1"
              icon={<Brain className="w-6 h-6" />}
              title="Instrument"
              body="Two lines attach forward hooks to your PyTorch model. The collector rings a fixed-size buffer in-process, with nothing transmitted until an incident fires. Low overhead is a hard design constraint — we will publish a measured p99 figure rather than an estimate."
              items={[
                "PyTorch adapter (shipped)",
                "ONNX Runtime and TensorRT (roadmap)",
                "ROS 2 topic, node, and lag monitoring",
                "Go edge agent for host metrics",
              ]}
            />
            <StepBlock
              step="2"
              icon={<Layers className="w-6 h-6" />}
              title="Correlate"
              body="On an incident trigger, the buffer flushes and joins the model timeline to system telemetry, ROS 2 topic health, and the deployment that was running — matched by weights hash."
              items={[
                "Model, sensor, and host state on one timeline",
                "7 system rules plus the AI rule engine",
                "Incidents grouped by release and weights hash",
                "Optional two-sentence LLM summary",
              ]}
            />
            <StepBlock
              step="3"
              icon={<RefreshCw className="w-6 h-6" />}
              title="Replay"
              body="Export a portable bundle any engineer can open. The sandbox that re-runs captured inputs against new weights — to prove a fix before it reaches the fleet — is the next thing we are building, not something you can run today."
              items={[
                "Replay bundle ZIP export (shipped)",
                "Deterministic replay sandbox (roadmap)",
                "Attention overlay on the failure frame (roadmap)",
                "Decision trace with ranked alternatives (roadmap)",
              ]}
            />
          </div>
        </div>
      </section>

      {/* Self-hosted */}
      <section className="py-24 border-t border-border/40">
        <div className="max-w-6xl mx-auto px-6">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-border/60 text-xs text-muted-foreground mb-6">
                <Lock className="w-3 h-3" />
                Self-hosted by default
              </div>
              <h2 className="text-3xl font-bold mb-6 leading-tight">
                Your camera data never leaves your VPC.
              </h2>
              <p className="text-muted-foreground leading-relaxed mb-6">
                Footage from a customer&apos;s warehouse is usually contractually
                un-exportable. That single fact kills most observability vendors
                in robotics procurement, so we built for it from the start.
              </p>
              <p className="text-muted-foreground leading-relaxed">
                Watchpoint runs entirely on your infrastructure. Model weights are
                hashed for lineage, never uploaded. LLM summaries are optional —
                with no API key configured, the rules engine degrades to
                deterministic text and every feature keeps working.
              </p>
            </div>

            <div className="space-y-4">
              <PrivacyRow
                icon={<Server className="w-4 h-4" />}
                title="Runs in your infrastructure"
                body="Docker Compose today; your own Postgres, your own storage."
              />
              <PrivacyRow
                icon={<ShieldCheck className="w-4 h-4" />}
                title="No outbound dependency"
                body="No telemetry home. The stack functions fully air-gapped."
              />
              <PrivacyRow
                icon={<GitBranch className="w-4 h-4" />}
                title="Weights hashed, not uploaded"
                body="Incidents tie to a weights hash so you can group by release."
              />
              <PrivacyRow
                icon={<Boxes className="w-4 h-4" />}
                title="Apache 2.0 core"
                body="Every collector is open source. Read it before you put it on a robot."
              />
            </div>
          </div>
        </div>
      </section>

      {/* Quickstart */}
      <section id="quickstart" className="py-24 border-t border-border/40">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold mb-4">Run the whole stack locally</h2>
          <p className="text-muted-foreground mb-8">
            Clone, compose up, seed. Three demo incidents, each carrying system
            telemetry and seeded AI-layer inferences — no account, no cloud. The
            seed is illustrative data, not a recording of a real robot.
          </p>

          <div className="bg-muted/50 border border-border/40 rounded-lg px-6 py-5 font-mono text-sm text-left space-y-1.5 overflow-x-auto">
            <div>
              <span className="text-muted-foreground select-none">$ </span>
              git clone {REPO_URL}.git
            </div>
            <div>
              <span className="text-muted-foreground select-none">$ </span>
              cd watchpoint/deploy/docker-compose &amp;&amp; docker compose up -d
            </div>
            <div>
              <span className="text-muted-foreground select-none">$ </span>
              curl -X POST localhost:8000/api/v1/seed/demo
            </div>
          </div>

          <div className="flex flex-wrap gap-4 justify-center mt-8">
            <Link href="/dashboard" className={cn(buttonVariants({ size: "lg" }), "gap-2")}>
              Or explore the hosted demo
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              href="/pricing"
              className={cn(buttonVariants({ variant: "outline", size: "lg" }))}
            >
              Become a design partner
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border/40 py-10">
        <div className="max-w-6xl mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Activity className="w-4 h-4" />
            Watchpoint — AI failure forensics for physical AI
          </div>
          <div className="flex items-center gap-5 text-xs text-muted-foreground">
            <Link href="/pricing" className="hover:text-foreground transition-colors">
              Pricing
            </Link>
            <a href={REPO_URL} className="hover:text-foreground transition-colors">
              GitHub
            </a>
            <Link href="/dashboard" className="hover:text-foreground transition-colors">
              Demo
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}

function CaptureLayer({
  icon,
  index,
  title,
  detail,
  captured,
}: {
  icon: React.ReactNode;
  index: string;
  title: string;
  detail: string;
  /** What the collectors record today. Everything else is stated as pending. */
  captured: string;
}) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-2 text-muted-foreground">
        {icon}
        <span className="text-xs font-mono">{index}</span>
      </div>
      <div className="font-semibold text-sm mb-1">{title}</div>
      <div className="text-sm text-muted-foreground leading-relaxed mb-2">
        {detail}
      </div>
      <div className="text-xs text-muted-foreground/70 leading-relaxed">
        {captured}
      </div>
    </div>
  );
}

function ContrastRow({
  label,
  answers,
  verdict,
  highlight = false,
}: {
  label: string;
  answers: string;
  verdict: string;
  highlight?: boolean;
}) {
  return (
    <div
      className={`rounded-xl border p-5 ${
        highlight ? "border-primary/40 bg-primary/5" : "border-border/40"
      }`}
    >
      <div className="text-sm font-semibold mb-2">{label}</div>
      <div className="text-sm text-muted-foreground mb-1">{answers}</div>
      <div
        className={`text-sm font-mono ${
          highlight ? "text-primary" : "text-muted-foreground/70"
        }`}
      >
        {verdict}
      </div>
    </div>
  );
}

/**
 * A rule's build state, which is deliberately not the same question as whether
 * its code is merged.
 *
 *   live    — runs end to end on data a collector actually captures
 *   demo    — rule is merged, but nothing produces its input yet, so it can
 *             only fire against seeded data
 *   roadmap — specified, not built
 *
 * The distinction exists because "merged" and "works on your robot" came apart:
 * AI-002 reads OODSignal rows, and the only writer of those is the demo seed.
 */
type RuleStatus = "live" | "demo" | "roadmap";

const RULE_STATUS_BADGE: Record<
  RuleStatus,
  { label: string; className: string } | null
> = {
  live: {
    label: "live",
    className: "border-green-500/20 bg-green-500/10 text-green-500",
  },
  demo: {
    label: "demo data only",
    className: "border-amber-500/20 bg-amber-500/10 text-amber-500",
  },
  roadmap: null,
};

function RuleCard({
  id,
  name,
  trigger,
  severity,
  status = "roadmap",
}: {
  id: string;
  name: string;
  trigger: string;
  severity: "critical" | "high" | "medium" | "low";
  status?: RuleStatus;
}) {
  const colors = {
    critical: "text-red-500 bg-red-500/10 border-red-500/20",
    high: "text-orange-500 bg-orange-500/10 border-orange-500/20",
    medium: "text-yellow-500 bg-yellow-500/10 border-yellow-500/20",
    low: "text-blue-500 bg-blue-500/10 border-blue-500/20",
  };

  const badge = RULE_STATUS_BADGE[status];

  return (
    <Card className="bg-card/50 border-border/40">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5 min-w-0">
            <span className="text-xs font-mono text-muted-foreground shrink-0">
              {id}
            </span>
            <CardTitle className="text-base truncate">{name}</CardTitle>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {badge && (
              <span
                className={`text-xs px-2 py-0.5 rounded-full border ${badge.className}`}
              >
                {badge.label}
              </span>
            )}
            <span
              className={`text-xs px-2 py-0.5 rounded-full border ${colors[severity]}`}
            >
              {severity}
            </span>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground leading-relaxed">{trigger}</p>
      </CardContent>
    </Card>
  );
}

function StepBlock({
  step,
  icon,
  title,
  body,
  items,
}: {
  step: string;
  icon: React.ReactNode;
  title: string;
  body: string;
  items: string[];
}) {
  return (
    <div className="border border-border/40 rounded-xl p-6">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center">
          {icon}
        </div>
        <div>
          <div className="text-xs font-mono text-muted-foreground">
            Step {step}
          </div>
          <h3 className="font-semibold">{title}</h3>
        </div>
      </div>
      <p className="text-sm text-muted-foreground leading-relaxed mb-4">{body}</p>
      <ul className="space-y-2">
        {items.map((item) => (
          <li
            key={item}
            className="text-sm text-muted-foreground flex items-start gap-2"
          >
            <span className="mt-1.5 w-1 h-1 rounded-full bg-current flex-shrink-0" />
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

function PrivacyRow({
  icon,
  title,
  body,
}: {
  icon: React.ReactNode;
  title: string;
  body: string;
}) {
  return (
    <div className="flex items-start gap-4 rounded-xl border border-border/40 p-5">
      <div className="w-9 h-9 rounded-lg bg-muted flex items-center justify-center shrink-0">
        {icon}
      </div>
      <div>
        <div className="text-sm font-semibold mb-1">{title}</div>
        <div className="text-sm text-muted-foreground leading-relaxed">{body}</div>
      </div>
    </div>
  );
}

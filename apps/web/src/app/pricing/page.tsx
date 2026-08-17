import type { Metadata } from "next";
import Link from "next/link";
import {
  Activity,
  ArrowRight,
  Check,
  Cloud,
  Handshake,
  Minus,
} from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

export const metadata: Metadata = {
  title: "Pricing — Watchpoint",
  description:
    "Self-hosted AI failure forensics for robotics teams. Open-source core, per-robot Team tier, and an early design-partner program.",
};

const REPO_URL = "https://github.com/sagarbpatel31/watchpoint";
const CONTACT_EMAIL = "sagarp220376@gmail.com";

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Nav */}
      <nav className="border-b border-border/40 backdrop-blur-sm sticky top-0 z-50 bg-background/80">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
              <Activity className="w-5 h-5 text-primary-foreground" />
            </div>
            <span className="text-lg font-bold tracking-tight">Watchpoint</span>
          </Link>
          <div className="flex items-center gap-5">
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

      {/* Header */}
      <section className="py-20 md:py-24">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-6">
            Priced per robot, not per gigabyte.
          </h1>
          <p className="text-lg text-muted-foreground leading-relaxed">
            Telemetry pricing punishes you for capturing the thing that explains
            the failure. Watchpoint charges by fleet size, so the incentive to
            instrument deeply stays intact.
          </p>
        </div>
      </section>

      {/* Tiers */}
      <section className="pb-8">
        <div className="max-w-6xl mx-auto px-6 grid lg:grid-cols-3 gap-6 items-start">
          <PlanCard
            name="Community"
            price="Free"
            cadence="self-hosted, forever"
            summary="The full forensics core, running entirely on your infrastructure."
            cta={{ label: "Read the source", href: REPO_URL, variant: "outline" }}
            features={[
              "Unlimited devices and users",
              "Model collector with PyTorch adapter",
              "ROS 2 collector and Go edge agent",
              "7 system rules + shipped AI rules",
              "Incident timeline and inference views",
              "Replay bundle ZIP export",
              "Community support via GitHub issues",
            ]}
          />

          <PlanCard
            name="Team"
            price="$49"
            cadence="per robot / month, billed annually"
            summary="For fleets past the point where one engineer can triage by hand."
            highlight
            badge="Most robotics teams"
            cta={{ label: "Talk to us", href: `mailto:${CONTACT_EMAIL}?subject=Watchpoint%20Team%20plan` }}
            features={[
              "Everything in Community",
              "Full AI rule taxonomy as it ships",
              "Deterministic replay sandbox (roadmap)",
              "Attention overlays and decision traces (roadmap)",
              "Cross-fleet baselines and regression grouping",
              "Guided upgrades and migration support",
              "Priority support, 1 business day response",
            ]}
            footnote="Minimum 10 robots. Robots in a bench or CI fleet aren't counted."
          />

          <PlanCard
            name="Enterprise"
            price="Custom"
            cadence="annual contract"
            summary="For teams with a safety case, an auditor, or an air gap."
            cta={{ label: "Contact sales", href: `mailto:${CONTACT_EMAIL}?subject=Watchpoint%20Enterprise`, variant: "outline" }}
            features={[
              "Everything in Team",
              "SSO / SAML and audit logging",
              "Air-gapped and on-prem deployment support",
              "Incident record exports for safety cases",
              "Custom rules built for your failure modes",
              "SLA with named support engineer",
              "Roadmap input and design review",
            ]}
          />
        </div>
      </section>

      {/* Design partner */}
      <section className="py-16">
        <div className="max-w-6xl mx-auto px-6">
          <Card className="border-primary/30 bg-primary/5">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2 text-primary">
                <Handshake className="w-4 h-4" />
                <span className="text-xs font-semibold uppercase tracking-wide">
                  Design partner program — open now
                </span>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-2 gap-8 items-start">
                <div>
                  <h2 className="text-2xl font-bold mb-3">
                    Free for 12 months. We build your failure mode.
                  </h2>
                  <p className="text-sm text-muted-foreground leading-relaxed mb-4">
                    We&apos;re taking a small number of design partners running
                    real fleets. You get the Team tier at no cost for a year, and
                    we implement the failure mode that costs your team the most
                    time as a first-class rule in the engine.
                  </p>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    In exchange we ask for honest feedback, an hour every two
                    weeks, and permission to reference your team once you&apos;re
                    happy with the results.
                  </p>
                </div>
                <div>
                  <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">
                    Good fit if you
                  </div>
                  <ul className="space-y-2 mb-6">
                    {[
                      "Run 5+ robots on ROS 2 or a custom autonomy stack",
                      "Have learned perception in production today",
                      "Lost more than a day to a field incident recently",
                      "Can self-host a Postgres and a container",
                    ].map((item) => (
                      <li key={item} className="flex items-start gap-2 text-sm">
                        <Check className="w-4 h-4 text-primary mt-0.5 shrink-0" />
                        <span className="text-muted-foreground">{item}</span>
                      </li>
                    ))}
                  </ul>
                  <a
                    href={`mailto:${CONTACT_EMAIL}?subject=Watchpoint%20design%20partner`}
                    className={cn(buttonVariants({ size: "lg" }), "gap-2")}
                  >
                    Apply as a design partner
                    <ArrowRight className="w-4 h-4" />
                  </a>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Hosted cloud */}
      <section className="pb-16">
        <div className="max-w-6xl mx-auto px-6">
          <div className="rounded-xl border border-border/40 p-6 flex flex-col md:flex-row md:items-center gap-6 justify-between">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center shrink-0">
                <Cloud className="w-5 h-5" />
              </div>
              <div>
                <div className="font-semibold mb-1">
                  Hosted cloud — not yet available
                </div>
                <p className="text-sm text-muted-foreground leading-relaxed max-w-2xl">
                  We deliberately built self-hosted first, because most robotics
                  teams cannot export customer camera data. A managed option is
                  planned for teams without that constraint. It isn&apos;t built
                  yet, and we&apos;d rather say so than take a waitlist deposit
                  on it.
                </p>
              </div>
            </div>
            <a
              href={`mailto:${CONTACT_EMAIL}?subject=Watchpoint%20hosted%20cloud%20interest`}
              className={cn(buttonVariants({ variant: "outline" }), "shrink-0")}
            >
              Tell us you want it
            </a>
          </div>
        </div>
      </section>

      {/* Comparison */}
      <section className="py-16 border-t border-border/40">
        <div className="max-w-4xl mx-auto px-6">
          <h2 className="text-2xl font-bold mb-8 text-center">
            What&apos;s in each plan
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border/40">
                  <th className="text-left font-medium text-muted-foreground py-3 pr-4">
                    Capability
                  </th>
                  <th className="text-center font-medium py-3 px-3 w-28">
                    Community
                  </th>
                  <th className="text-center font-medium py-3 px-3 w-28">Team</th>
                  <th className="text-center font-medium py-3 px-3 w-28">
                    Enterprise
                  </th>
                </tr>
              </thead>
              <tbody>
                <CompareRow label="Self-hosted deployment" community team enterprise />
                <CompareRow label="Model collector + ROS 2 + edge agent" community team enterprise />
                <CompareRow label="System rules engine (7 rules)" community team enterprise />
                <CompareRow label="Shipped AI rules (AI-001–003)" community team enterprise />
                <CompareRow label="Replay bundle export" community team enterprise />
                <CompareRow label="Full AI taxonomy (AI-004–008)" team enterprise note="roadmap" />
                <CompareRow label="Replay sandbox" team enterprise note="roadmap" />
                <CompareRow label="Cross-fleet baselines" team enterprise />
                <CompareRow label="Priority support SLA" team enterprise />
                <CompareRow label="SSO / SAML + audit log" enterprise />
                <CompareRow label="Air-gapped deployment support" enterprise />
                <CompareRow label="Custom rules built for you" enterprise />
              </tbody>
            </table>
          </div>
          <p className="text-xs text-muted-foreground mt-6 text-center">
            Items marked <span className="font-mono">roadmap</span>{" "}
            are specified but not merged. Team and Enterprise include them as
            they ship; we don&apos;t bill for them before that.
          </p>
        </div>
      </section>

      {/* FAQ */}
      <section className="py-16 border-t border-border/40">
        <div className="max-w-3xl mx-auto px-6">
          <h2 className="text-2xl font-bold mb-8 text-center">Questions</h2>
          <div className="space-y-6">
            <Faq
              q="What exactly counts as a robot?"
              a="A physical unit running a collector and reporting under its own device ID. Bench rigs, simulation, and CI fleets are free and uncounted — we don't want to price you out of testing."
            />
            <Faq
              q="Is the Community tier crippled?"
              a="No. It's the complete forensics core: every collector, the system rules engine, the AI rules that have shipped, and bundle export. Paid tiers add fleet-scale analysis, the replay sandbox, and support — not access to your own data."
            />
            <Faq
              q="What's the license?"
              a="The core is Apache 2.0 — every collector, the API, the rules engine, and the dashboard. Anything that runs on your robot is Apache-licensed without exception, so you can audit it before you deploy it. Commercial features like SSO and cross-fleet rollups are licensed separately and live outside that tree."
            />
            <Faq
              q="Do you ever see our camera data?"
              a="No. Self-hosted means the stack runs in your VPC with your Postgres and your storage. Model weights are hashed for lineage, never uploaded. With no Anthropic key set, the LLM summary degrades to deterministic rules text and nothing leaves your network at all."
            />
            <Faq
              q="What happens if we stop paying?"
              a="You fall back to Community. It's self-hosted, so your data stays where it already is — there is no hostage situation and no export scramble."
            />
            <Faq
              q="Why is pricing per robot instead of per data volume?"
              a="Volume pricing makes you capture less exactly when you should capture more. The whole product depends on the failure frame being in the buffer, so we refuse to charge in a way that discourages that."
            />
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
            <Link href="/" className="hover:text-foreground transition-colors">
              Home
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

function PlanCard({
  name,
  price,
  cadence,
  summary,
  features,
  cta,
  highlight = false,
  badge,
  footnote,
}: {
  name: string;
  price: string;
  cadence: string;
  summary: string;
  features: string[];
  cta: { label: string; href: string; variant?: "default" | "outline" };
  highlight?: boolean;
  badge?: string;
  footnote?: string;
}) {
  return (
    <div
      className={`rounded-xl border p-6 h-full flex flex-col ${
        highlight ? "border-primary/40 bg-primary/5" : "border-border/40"
      }`}
    >
      <div className="flex items-center justify-between mb-3">
        <h2 className="font-semibold">{name}</h2>
        {badge && (
          <span className="text-xs px-2 py-0.5 rounded-full border border-primary/30 bg-primary/10 text-primary">
            {badge}
          </span>
        )}
      </div>
      <div className="mb-1">
        <span className="text-3xl font-bold">{price}</span>
      </div>
      <div className="text-xs text-muted-foreground mb-4">{cadence}</div>
      <p className="text-sm text-muted-foreground leading-relaxed mb-6">
        {summary}
      </p>
      <ul className="space-y-2.5 mb-6 flex-1">
        {features.map((f) => (
          <li key={f} className="flex items-start gap-2 text-sm">
            <Check className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
            <span className="text-muted-foreground">{f}</span>
          </li>
        ))}
      </ul>
      {footnote && (
        <p className="text-xs text-muted-foreground mb-4">{footnote}</p>
      )}
      <a
        href={cta.href}
        className={cn(
          buttonVariants({ variant: cta.variant ?? "default", size: "lg" }),
          "w-full",
        )}
      >
        {cta.label}
      </a>
    </div>
  );
}

function CompareRow({
  label,
  community = false,
  team = false,
  enterprise = false,
  note,
}: {
  label: string;
  community?: boolean;
  team?: boolean;
  enterprise?: boolean;
  note?: string;
}) {
  return (
    <tr className="border-b border-border/20">
      <td className="py-3 pr-4 text-muted-foreground">
        {label}
        {note && (
          <span className="ml-2 text-xs font-mono text-muted-foreground/60">
            {note}
          </span>
        )}
      </td>
      <Cell on={community} />
      <Cell on={team} />
      <Cell on={enterprise} />
    </tr>
  );
}

function Cell({ on }: { on: boolean }) {
  return (
    <td className="py-3 px-3 text-center">
      {on ? (
        <Check className="w-4 h-4 text-primary inline" />
      ) : (
        <Minus className="w-4 h-4 text-muted-foreground/30 inline" />
      )}
    </td>
  );
}

function Faq({ q, a }: { q: string; a: string }) {
  return (
    <div className="border-b border-border/20 pb-6 last:border-0">
      <h3 className="font-semibold mb-2">{q}</h3>
      <p className="text-sm text-muted-foreground leading-relaxed">{a}</p>
    </div>
  );
}

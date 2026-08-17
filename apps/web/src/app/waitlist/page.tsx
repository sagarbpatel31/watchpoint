import Link from "next/link";
import { ArrowRight, Eye, Zap, ShieldAlert, BarChart2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

export const metadata = {
  title: "Join the Waitlist — Watchpoint",
  description:
    "AI failure forensics for physical AI. When your robot fails, we tell you why — at the AI layer.",
};

export default function WaitlistPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Nav */}
      <nav className="border-b border-border/50">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <span className="font-bold text-sm tracking-tight">Watchpoint</span>
          <Link
            href="/login"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Sign in →
          </Link>
        </div>
      </nav>

      <main className="max-w-3xl mx-auto px-6 py-20">
        {/* Hero */}
        <div className="text-center mb-14">
          <div className="inline-flex items-center gap-2 text-xs font-medium bg-primary/10 text-primary rounded-full px-3 py-1 mb-6">
            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
            Early Access
          </div>

          <h1 className="text-4xl font-bold tracking-tight mb-4 leading-tight">
            When your robot fails,{" "}
            <span className="text-primary">we tell you why</span>
            <br />
            — at the AI layer
          </h1>

          <p className="text-lg text-muted-foreground max-w-xl mx-auto leading-relaxed">
            Watchpoint is AI failure forensics for physical AI systems. Captures model inputs,
            outputs, confidence, and attention at incident time — so you can replay and prove
            root cause, not just guess.
          </p>
        </div>

        {/* The gap */}
        <Card className="mb-10 border-border/50">
          <CardContent className="pt-6">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4">
              What existing tools miss
            </p>
            <div className="space-y-3">
              {[
                {
                  icon: Eye,
                  text: "What the model saw — synced sensor frames, exact inputs at failure time",
                },
                {
                  icon: BarChart2,
                  text: "What the model predicted — outputs, confidence scores, attention maps",
                },
                {
                  icon: Zap,
                  text: "Whether the input was OOD — embedding distance from training distribution",
                },
                {
                  icon: ShieldAlert,
                  text: "Why the policy failed — decision vs perception mismatch traced to root cause",
                },
              ].map(({ icon: Icon, text }) => (
                <div key={text} className="flex items-start gap-3">
                  <Icon className="w-4 h-4 text-primary mt-0.5 shrink-0" />
                  <span className="text-sm text-muted-foreground">{text}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Waitlist form */}
        <div className="text-center">
          <p className="text-sm text-muted-foreground mb-6">
            Built for robotics teams running ROS 2, PyTorch, ONNX, or TensorRT on edge hardware.
          </p>

          {/* Tally embed — replace TALLY_FORM_ID with your actual Tally form ID */}
          <a
            href="https://tally.so/r/TALLY_FORM_ID"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 bg-primary text-primary-foreground font-semibold px-8 py-3 rounded-lg hover:opacity-90 transition-opacity text-sm"
          >
            Join the waitlist
            <ArrowRight className="w-4 h-4" />
          </a>

          <p className="text-xs text-muted-foreground mt-4">
            No spam. Early access for robotics teams building with physical AI.
          </p>
        </div>

        {/* Social proof / context */}
        <div className="mt-16 pt-10 border-t border-border/50 text-center">
          <p className="text-xs text-muted-foreground">
            Watchpoint · AI failure forensics for physical AI ·{" "}
            <a
              href="https://github.com/sagarbpatel31/watchpoint"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-foreground transition-colors"
            >
              Open source
            </a>
          </p>
        </div>
      </main>
    </div>
  );
}

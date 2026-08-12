"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Brain, ChevronRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Navbar } from "@/components/layout/navbar";
import { AttentionOverlay } from "@/components/ai/AttentionOverlay";
import type { AttentionResponse, Inference } from "@/types/ai_layer";
import { apiFetch } from "@/lib/api-client";

export default function InferenceDetailPage() {
  const params = useParams();
  const inferenceId = params.id as string;

  const [inference, setInference] = useState<Inference | null>(null);
  const [attention, setAttention] = useState<AttentionResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [infData, attData] = await Promise.all([
          apiFetch<Inference>(`/inferences/${inferenceId}`),
          apiFetch<AttentionResponse>(`/inferences/${inferenceId}/attention`),
        ]);
        setInference(infData);
        setAttention(attData);
      } catch (err) {
        console.error("Failed to load inference:", err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [inferenceId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <Navbar />
        <main className="max-w-5xl mx-auto px-6 py-8">
          <p className="text-muted-foreground">Loading inference...</p>
        </main>
      </div>
    );
  }

  if (!inference) {
    return (
      <div className="min-h-screen bg-background">
        <Navbar />
        <main className="max-w-5xl mx-auto px-6 py-8">
          <p className="text-muted-foreground">Inference not found.</p>
        </main>
      </div>
    );
  }

  const confidenceColor =
    inference.confidence == null
      ? "text-muted-foreground"
      : inference.confidence < 0.5
        ? "text-red-500"
        : inference.confidence < 0.75
          ? "text-yellow-500"
          : "text-green-500";

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="max-w-5xl mx-auto px-6 py-8">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-sm text-muted-foreground mb-6">
          {inference.incident_id ? (
            <>
              <Link
                href={`/incidents/${inference.incident_id}`}
                className="hover:text-foreground transition-colors flex items-center gap-1"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                Incident
              </Link>
              <ChevronRight className="w-3.5 h-3.5" />
            </>
          ) : (
            <Link
              href="/dashboard"
              className="hover:text-foreground transition-colors flex items-center gap-1"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              Dashboard
            </Link>
          )}
          <span className="text-foreground font-mono text-xs">{inferenceId}</span>
        </div>

        {/* Header */}
        <div className="flex items-start justify-between mb-8">
          <div>
            <h1 className="text-xl font-bold flex items-center gap-2 mb-1">
              <Brain className="w-5 h-5 text-primary" />
              Inference Detail
            </h1>
            <p className="text-sm text-muted-foreground font-mono">
              Layer: {inference.layer_name ?? "top-level"}
            </p>
          </div>
          {inference.confidence != null && (
            <Badge variant="outline" className={`${confidenceColor} border-current`}>
              {(inference.confidence * 100).toFixed(1)}% confidence
            </Badge>
          )}
        </div>

        <div className="grid md:grid-cols-2 gap-4 mb-6">
          {/* Metadata */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Capture Metadata</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="space-y-2 text-sm">
                {(
                  [
                    ["Inference ID", inference.id],
                    ["Model Run", inference.model_run_id],
                    ["Device", inference.device_id],
                    ["Timestamp (ns)", inference.timestamp_ns.toString()],
                    ["Latency", inference.latency_ms != null ? `${inference.latency_ms.toFixed(2)} ms` : "—"],
                  ] as [string, string][]
                ).map(([label, value]) => (
                  <div key={label} className="flex justify-between gap-4">
                    <dt className="text-muted-foreground shrink-0">{label}</dt>
                    <dd className="font-mono text-xs text-right truncate">{value}</dd>
                  </div>
                ))}
              </dl>
            </CardContent>
          </Card>

          {/* Output stats */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Output Statistics</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="space-y-2 text-sm">
                {(
                  [
                    ["Confidence", inference.confidence != null ? `${(inference.confidence * 100).toFixed(2)}%` : "—"],
                    ["Output mean", inference.output_mean?.toFixed(6) ?? "—"],
                    ["Output std", inference.output_std?.toFixed(6) ?? "—"],
                  ] as [string, string][]
                ).map(([label, value]) => (
                  <div key={label} className="flex justify-between gap-4">
                    <dt className="text-muted-foreground">{label}</dt>
                    <dd className="font-mono text-xs">{value}</dd>
                  </div>
                ))}
              </dl>
            </CardContent>
          </Card>
        </div>

        {/* Attention overlay */}
        <AttentionOverlay
          heatmap={attention?.heatmap ?? null}
          status={attention?.status ?? "unavailable"}
          layerName={attention?.layer_name ?? inference.layer_name}
        />
      </main>
    </div>
  );
}

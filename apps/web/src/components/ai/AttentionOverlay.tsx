"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Eye, EyeOff } from "lucide-react";

interface AttentionOverlayProps {
  heatmap: number[][] | null;
  status: "available" | "unavailable";
  layerName: string | null;
}

/**
 * Renders an 8×8 Grad-CAM attention heatmap as a color grid.
 * Cold (low attention) = blue tint, Hot (high attention) = red.
 * Mirrors spatial layout of camera frame.
 */
export function AttentionOverlay({ heatmap, status, layerName }: AttentionOverlayProps) {
  if (status === "unavailable" || !heatmap) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <EyeOff className="w-4 h-4 text-muted-foreground" />
            Attention / Saliency Map
            <Badge variant="outline" className="text-muted-foreground text-xs">
              unavailable
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Grad-CAM not computed for this inference.{" "}
            <span className="opacity-60">
              Attach model-collector with{" "}
              <code className="text-xs font-mono">layer_names=[&quot;...&quot;]</code> to enable.
            </span>
          </p>
        </CardContent>
      </Card>
    );
  }

  // Find max value for normalisation
  const flat = heatmap.flat();
  const maxVal = Math.max(...flat);
  const minVal = Math.min(...flat);
  const range = maxVal - minVal || 1;

  function heatmapColor(value: number): string {
    // Normalize 0→1
    const t = (value - minVal) / range;
    // Cold (t=0): rgba(59,130,246,0.15) — blue tint
    // Warm (t=0.5): rgba(234,179,8,0.6) — yellow
    // Hot (t=1): rgba(239,68,68,0.9) — red
    if (t < 0.5) {
      const tt = t * 2;
      const r = Math.round(59 + (234 - 59) * tt);
      const g = Math.round(130 + (179 - 130) * tt);
      const b = Math.round(246 + (8 - 246) * tt);
      const a = 0.15 + 0.45 * tt;
      return `rgba(${r},${g},${b},${a.toFixed(2)})`;
    } else {
      const tt = (t - 0.5) * 2;
      const r = Math.round(234 + (239 - 234) * tt);
      const g = Math.round(179 + (68 - 179) * tt);
      const b = Math.round(8 + (68 - 8) * tt);
      const a = 0.60 + 0.30 * tt;
      return `rgba(${r},${g},${b},${a.toFixed(2)})`;
    }
  }

  const rows = heatmap.length;
  const cols = heatmap[0]?.length ?? 0;

  // Find peak attention region for label
  let peakRow = 0, peakCol = 0, peakVal = -1;
  heatmap.forEach((row, r) =>
    row.forEach((val, c) => {
      if (val > peakVal) { peakVal = val; peakRow = r; peakCol = c; }
    })
  );
  const quadrant = `${peakRow < rows / 2 ? "top" : "bottom"}-${peakCol < cols / 2 ? "left" : "right"}`;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center gap-2">
          <Eye className="w-4 h-4 text-primary" />
          Attention / Saliency Map
          <Badge variant="outline" className="text-green-500 border-green-500/30 text-xs">
            available
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {/* Legend */}
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>
              Layer:{" "}
              <code className="font-mono text-foreground">{layerName ?? "unknown"}</code>
            </span>
            <span>
              Peak activation:{" "}
              <span className="text-red-400 font-medium">{quadrant}</span>{" "}
              ({(peakVal * 100).toFixed(0)}%)
            </span>
          </div>

          {/* Heatmap grid */}
          <div className="relative rounded-md overflow-hidden border border-border/50">
            {/* Placeholder camera frame background */}
            <div className="w-full aspect-video bg-zinc-900 flex items-center justify-center">
              <span className="text-xs text-zinc-600 absolute select-none">camera frame</span>
            </div>

            {/* Attention overlay */}
            <div
              className="absolute inset-0"
              style={{
                display: "grid",
                gridTemplateColumns: `repeat(${cols}, 1fr)`,
                gridTemplateRows: `repeat(${rows}, 1fr)`,
              }}
            >
              {heatmap.map((row, r) =>
                row.map((val, c) => (
                  <div
                    key={`${r}-${c}`}
                    title={`(${r},${c}): ${(val * 100).toFixed(0)}%`}
                    style={{ backgroundColor: heatmapColor(val) }}
                  />
                ))
              )}
            </div>
          </div>

          {/* Color scale legend */}
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <div
              className="h-2 flex-1 rounded"
              style={{
                background:
                  "linear-gradient(to right, rgba(59,130,246,0.15), rgba(234,179,8,0.6), rgba(239,68,68,0.9))",
              }}
            />
            <div className="flex justify-between w-full max-w-[160px]">
              <span>low</span>
              <span>attention</span>
              <span>high</span>
            </div>
          </div>

          <p className="text-xs text-muted-foreground">
            Heatmap shows where the model attended during this inference frame.
            Red regions drove the prediction.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

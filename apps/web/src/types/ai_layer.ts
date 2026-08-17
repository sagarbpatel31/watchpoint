/**
 * TypeScript types for the Watchpoint AI layer.
 * Mirror of apps/api/app/schemas/ai_layer.py response models.
 */

export type Framework = "pytorch" | "onnx" | "tensorrt";

export interface ModelRun {
  id: string;
  device_id: string;
  framework: Framework;
  model_name: string;
  weights_hash: string | null;
  started_at: string | null;
  created_at: string;
}

export interface Inference {
  id: string;
  model_run_id: string;
  device_id: string;
  incident_id: string | null;
  timestamp_ns: number;
  confidence: number | null;
  latency_ms: number | null;
  layer_name: string | null;
  output_mean: number | null;
  output_std: number | null;
}

export interface InferenceListResponse {
  inferences: Inference[];
  total: number;
}

export interface AttentionResponse {
  inference_id: string;
  attention_ref: string | null;
  layer_name: string | null;
  /** "available" when Grad-CAM has been computed; "unavailable" otherwise */
  status: "available" | "unavailable";
  /** 8×8 normalized attention grid (0.0–1.0). null when status="unavailable". */
  heatmap: number[][] | null;
}

export interface Decision {
  id: string;
  inference_id: string;
  policy_name: string;
  action: string;
  confidence: number | null;
}

export interface OODSignal {
  id: string;
  inference_id: string;
  signal_type: string;
  score: number;
  threshold: number;
  is_ood: boolean;
}

export type ReplayJobStatus = "pending" | "running" | "completed" | "failed";

export interface ReplayJob {
  id: string;
  incident_id: string;
  status: ReplayJobStatus;
  created_at: string;
  completed_at: string | null;
  result: Record<string, unknown> | null;
  error: string | null;
}

import { useState } from "react";
import { Activity, Database, Radar } from "lucide-react";
import { Panel } from "../components/Panel";
import { StatusPill } from "../components/StatusPill";
import { api } from "../services/api";
import type { SpectralDetectionPayload, SpectralDetectionResponse, SpectralIngestResponse } from "../types/api";

const samplePayload: SpectralDetectionPayload = {
  source_reference: `frontend_spectral_sample_${new Date().toISOString()}`,
  red_band: [
    [0.035, 0.036, 0.034],
    [0.034, 0.045, 0.047],
    [0.033, 0.046, 0.05]
  ],
  nir_band: [
    [0.04, 0.041, 0.04],
    [0.039, 0.085, 0.09],
    [0.04, 0.088, 0.096]
  ],
  swir_band: [
    [0.03, 0.031, 0.03],
    [0.03, 0.048, 0.049],
    [0.03, 0.047, 0.052]
  ],
  cloud_mask: [
    [false, false, false],
    [false, false, false],
    [false, false, false]
  ]
};

export function SpectralDetectionPage() {
  const [result, setResult] = useState<SpectralDetectionResponse | SpectralIngestResponse>();
  const [busy, setBusy] = useState<string>();
  const [error, setError] = useState<string>();

  const runAction = async (label: string, action: () => Promise<SpectralDetectionResponse | SpectralIngestResponse>) => {
    setBusy(label);
    setError(undefined);
    try {
      setResult(await action());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Spectral request failed");
    } finally {
      setBusy(undefined);
    }
  };

  const ingest = result && "persisted" in result ? result : undefined;
  const summary = result?.summary;

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">Spectral Detection</h1>
          <p className="mt-1 text-sm text-slate-400">Sentinel-2-compatible NDVI/FAI detection with controlled operational ingest.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="inline-flex items-center gap-2 rounded bg-white/10 px-3 py-2 text-sm text-white ring-1 ring-white/10 hover:bg-white/15" onClick={() => runAction("demo", api.spectralDemo)} disabled={!!busy}>
            <Radar size={16} /> Demo
          </button>
          <button className="inline-flex items-center gap-2 rounded bg-cyanline/15 px-3 py-2 text-sm text-cyanline ring-1 ring-cyanline/20 hover:bg-cyanline/20" onClick={() => runAction("detect", () => api.spectralDetect(samplePayload))} disabled={!!busy}>
            <Activity size={16} /> Detect Sample
          </button>
          <button className="inline-flex items-center gap-2 rounded bg-emerald-500/15 px-3 py-2 text-sm text-emerald-200 ring-1 ring-emerald-400/20 hover:bg-emerald-500/20" onClick={() => runAction("ingest", () => api.spectralDetectAndIngest({ ...samplePayload, source_reference: `frontend_spectral_ingest_${new Date().toISOString()}` }, true))} disabled={!!busy}>
            <Database size={16} /> Ingest + Drift
          </button>
        </div>
      </div>

      {error ? <div className="rounded border border-rose-400/25 bg-rose-500/10 p-3 text-sm text-rose-100">{error}</div> : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Metric label="Detected pixels" value={summary?.detected_pixels ?? 0} />
        <Metric label="Confidence" value={summary ? `${Math.round(summary.confidence_score * 100)}%` : "0%"} />
        <Metric label="Polygons" value={summary?.generated_polygons ?? result?.polygon_features.length ?? 0} />
        <Metric label="Density" value={summary?.density_level ?? "none"} />
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Panel title="Detection Result" action={summary ? <StatusPill value={summary.confidence_score >= 0.65 ? "high" : "low"} /> : undefined}>
          <div className="grid gap-3 text-sm text-slate-300 md:grid-cols-2">
            <p>Algorithm: <span className="text-white">{result?.algorithm ?? "waiting"}</span></p>
            <p>Point features: <span className="text-white">{result?.features.length ?? 0}</span></p>
            <p>Polygon features: <span className="text-white">{result?.polygon_features.length ?? 0}</span></p>
            <p>Cloud mask: <span className="text-white">{result?.masking?.cloud_mask_applied ? "applied" : "not applied"}</span></p>
          </div>
        </Panel>

        <Panel title="Operational Ingest">
          <div className="grid gap-3 text-sm text-slate-300 md:grid-cols-2">
            <p>Persisted: <span className="text-white">{ingest ? String(ingest.persisted) : "not run"}</span></p>
            <p>Observations: <span className="text-white">{ingest?.created_observations ?? 0}</span></p>
            <p>Patches: <span className="text-white">{ingest?.created_patches ?? 0}</span></p>
            <p>Collection zones: <span className="text-white">{ingest?.created_collection_zones ?? 0}</span></p>
            <p>Drift zones: <span className="text-white">{ingest?.created_drift_zone_ids.length ?? 0}</span></p>
            <p>Forecast tracks: <span className="text-white">{ingest?.drift_predictions.length ?? 0}</span></p>
          </div>
        </Panel>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <Panel title={label}>
      <p className="text-2xl font-semibold text-white">{value}</p>
    </Panel>
  );
}

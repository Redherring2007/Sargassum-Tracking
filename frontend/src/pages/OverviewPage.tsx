import { AlertTriangle, ClipboardList, Radar, Ship, Waves, RefreshCw } from "lucide-react";
import { KpiCard } from "../components/KpiCard";
import { Panel } from "../components/Panel";
import { StatusPill } from "../components/StatusPill";
import { OperationsMap } from "../maps/OperationsMap";
import { useOperationsData } from "../hooks/useOperationsData";
import { api } from "../services/api";

export function OverviewPage() {
  const data = useOperationsData();
  const seed = async () => {
    await api.seedDemo();
    await data.refresh();
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-sm uppercase tracking-wide text-cyanline">Commercial operations dashboard</p>
          <h1 className="mt-1 text-2xl font-semibold text-white md:text-3xl">Sargassum intelligence and collection command</h1>
          <p className="mt-2 max-w-3xl text-sm text-slate-400">
            Live-ready monitoring for offshore patches, coastline risk, vessel dispatch, task cost, and client impact.
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={data.refresh} className="inline-flex items-center gap-2 rounded bg-white/10 px-3 py-2 text-sm text-white ring-1 ring-white/15">
            <RefreshCw size={16} /> Refresh
          </button>
          <button onClick={seed} className="rounded bg-cyanline px-3 py-2 text-sm font-semibold text-ink">Seed demo</button>
        </div>
      </div>

      {data.error ? (
        <div className="rounded-lg border border-amber-400/30 bg-amber-500/10 p-4 text-sm text-amber-100">
          {data.error}. Start the backend and seed demo data to activate the dashboard.
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-6">
        <KpiCard label="Observations" value={data.summary?.observations ?? "—"} subtext="Manual, drone, satellite-ready" Icon={Radar} />
        <KpiCard label="Patches" value={data.summary?.patches ?? "—"} subtext={`${data.summary?.critical_patches ?? 0} critical offshore masses`} Icon={Waves} />
        <KpiCard label="Vessels" value={data.summary?.vessels ?? "—"} subtext="GPS tasking enabled" Icon={Ship} />
        <KpiCard label="Tasks" value={data.summary?.active_tasks ?? "—"} subtext="Assigned or in progress" Icon={ClipboardList} />
        <KpiCard label="Alerts" value={data.summary?.unread_alerts ?? "—"} subtext="Unread operational alerts" Icon={AlertTriangle} />
        <KpiCard label="Routes" value={data.routes.length} subtext="Cost-ranked recommendations" Icon={Radar} />
      </div>

      <div className="grid gap-5 xl:grid-cols-[1fr_420px]">
        <OperationsMap {...data} />
        <div className="space-y-5">
          <Panel title="Top route recommendation">
            {data.routes[0] ? (
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-lg font-semibold text-white">{data.routes[0].vessel_name}</p>
                    <p className="text-sm text-slate-400">{data.routes[0].zone_name}</p>
                  </div>
                  <StatusPill value={data.routes[0].action} />
                </div>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <Metric label="Score" value={data.routes[0].recommendation_score.toFixed(1)} />
                  <Metric label="Distance" value={`${data.routes[0].distance_nm} nm`} />
                  <Metric label="Cost" value={`$${data.routes[0].estimated_cost.toLocaleString()}`} />
                  <Metric label="Duration" value={`${data.routes[0].estimated_time_to_complete} h`} />
                </div>
                <p className="text-sm text-slate-300">{data.routes[0].reasoning_summary}</p>
              </div>
            ) : (
              <p className="text-sm text-slate-400">No route recommendations yet.</p>
            )}
          </Panel>
          <Panel title="Priority alerts">
            <div className="space-y-3">
              {data.alerts.slice(0, 4).map((alert) => (
                <div key={alert.id} className="rounded border border-white/10 bg-white/[0.03] p-3">
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <StatusPill value={alert.severity} />
                    <span className="text-xs text-slate-500">{new Date(alert.created_at).toLocaleString()}</span>
                  </div>
                  <p className="text-sm text-slate-100">{alert.message}</p>
                  {alert.recommended_action ? <p className="mt-2 text-xs text-cyan-100">{alert.recommended_action}</p> : null}
                </div>
              ))}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-white/10 bg-white/[0.03] p-3">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 font-semibold text-white">{value}</p>
    </div>
  );
}

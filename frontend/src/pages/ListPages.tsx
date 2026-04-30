import { Panel } from "../components/Panel";
import { StatusPill } from "../components/StatusPill";
import { useOperationsData } from "../hooks/useOperationsData";

export function ClientsPage() {
  const { sites } = useOperationsData();
  return <SimpleList title="Client Sites" items={sites.map((s) => ({ title: s.site_name, subtitle: `${s.site_type} • priority ${s.priority_level}`, status: s.current_risk, detail: s.notes }))} />;
}

export function VesselsPage() {
  const { vessels } = useOperationsData();
  return <SimpleList title="Vessel Tracking" items={vessels.map((v) => ({ title: v.vessel_name, subtitle: `${v.vessel_type} • ${v.home_port}`, status: v.status, detail: `${v.collection_capacity_kg.toLocaleString()} kg capacity • ${v.working_speed_knots} kt working speed` }))} />;
}

export function TasksPage() {
  const { tasks } = useOperationsData();
  return <SimpleList title="Collection Task Board" items={tasks.map((t) => ({ title: t.task_reference, subtitle: `${t.estimated_volume_kg.toLocaleString()} kg • $${t.estimated_cost.toLocaleString()}`, status: t.status, detail: `Priority ${t.priority} • duration ${t.estimated_duration} h` }))} />;
}

export function PredictionsPage() {
  const { patches, zones } = useOperationsData();
  return <SimpleList title="Drift Predictions" items={[...patches.map((p) => ({ title: p.patch_reference, subtitle: `${p.movement_direction_degrees}° at ${p.movement_speed_knots} kt`, status: p.severity, detail: p.notes })), ...zones.map((z) => ({ title: z.zone_name, subtitle: `${z.estimated_volume_kg.toLocaleString()} kg predicted collection`, status: z.severity, detail: z.notes }))]} />;
}

export function AlertsPage() {
  const { alerts } = useOperationsData();
  return <SimpleList title="Alerts" items={alerts.map((a) => ({ title: a.alert_type.replace(/_/g, " "), subtitle: a.message, status: a.severity, detail: a.recommended_action }))} />;
}

export function AdminPage() {
  const data = useOperationsData();
  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-semibold text-white">Admin Dashboard</h1>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {[
          ["Observations", data.summary?.observations ?? 0],
          ["Patches", data.summary?.patches ?? 0],
          ["Vessels", data.summary?.vessels ?? 0],
          ["Active tasks", data.summary?.active_tasks ?? 0],
          ["Unread alerts", data.summary?.unread_alerts ?? 0],
          ["Route recommendations", data.routes.length]
        ].map(([label, value]) => (
          <Panel key={label} title={String(label)}>
            <p className="text-3xl font-semibold text-white">{value}</p>
            <p className="mt-2 text-sm text-slate-400">API-managed module ready for role gating and audit logs.</p>
          </Panel>
        ))}
      </div>
    </div>
  );
}

export function SettingsPage() {
  return (
    <Panel title="System Settings">
      <div className="grid gap-3 md:grid-cols-2">
        {["JWT auth placeholder", "Subscription plans", "API keys", "White-label dashboards", "Report exports", "Live data adapters"].map((item) => (
          <div key={item} className="rounded border border-white/10 bg-white/[0.03] p-3 text-sm text-slate-200">{item}</div>
        ))}
      </div>
    </Panel>
  );
}

function SimpleList({ title, items }: { title: string; items: { title: string; subtitle: string; status: string; detail?: string }[] }) {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold text-white">{title}</h1>
      <div className="grid gap-4 xl:grid-cols-2">
        {items.map((item, index) => (
          <Panel key={`${item.title}-${index}`} title={item.title} action={<StatusPill value={item.status} />}>
            <p className="text-sm text-slate-300">{item.subtitle}</p>
            {item.detail ? <p className="mt-3 text-sm text-slate-400">{item.detail}</p> : null}
          </Panel>
        ))}
      </div>
    </div>
  );
}

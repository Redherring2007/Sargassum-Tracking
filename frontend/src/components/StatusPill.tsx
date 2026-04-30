import type { Severity } from "../types/api";

const severityClasses: Record<string, string> = {
  low: "bg-emerald-500/15 text-emerald-200 ring-emerald-400/30",
  medium: "bg-sky-500/15 text-sky-200 ring-sky-400/30",
  high: "bg-amber-500/15 text-amber-100 ring-amber-400/30",
  critical: "bg-rose-500/15 text-rose-100 ring-rose-400/30",
  idle: "bg-emerald-500/15 text-emerald-100 ring-emerald-400/30",
  assigned: "bg-sky-500/15 text-sky-100 ring-sky-400/30",
  en_route: "bg-cyan-500/15 text-cyan-100 ring-cyan-400/30",
  collecting: "bg-lime-500/15 text-lime-100 ring-lime-400/30",
  returning: "bg-amber-500/15 text-amber-100 ring-amber-400/30",
  offline: "bg-slate-500/15 text-slate-200 ring-slate-400/30",
  proposed: "bg-slate-500/15 text-slate-100 ring-slate-400/30",
  completed: "bg-emerald-500/15 text-emerald-100 ring-emerald-400/30"
};

export function StatusPill({ value }: { value: Severity | string }) {
  return (
    <span className={`inline-flex items-center rounded px-2 py-1 text-xs font-medium ring-1 ${severityClasses[value] || severityClasses.medium}`}>
      {value.replace("_", " ")}
    </span>
  );
}

import type { LucideIcon } from "lucide-react";

export function KpiCard({
  label,
  value,
  subtext,
  Icon
}: {
  label: string;
  value: string | number;
  subtext: string;
  Icon: LucideIcon;
}) {
  return (
    <div className="rounded-lg border border-white/10 bg-panel/85 p-4 shadow-command">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
          <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
        </div>
        <div className="grid h-10 w-10 place-items-center rounded bg-cyanline/10 text-cyanline ring-1 ring-cyanline/25">
          <Icon size={20} />
        </div>
      </div>
      <p className="mt-3 text-sm text-slate-400">{subtext}</p>
    </div>
  );
}

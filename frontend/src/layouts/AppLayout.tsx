import { Bell, Map, Menu, Settings, Ship, ClipboardList, Waves, Users, ActivitySquare } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";
import { useState } from "react";

const nav = [
  { to: "/", label: "Overview", Icon: ActivitySquare },
  { to: "/map", label: "Map", Icon: Map },
  { to: "/clients", label: "Clients", Icon: Users },
  { to: "/vessels", label: "Vessels", Icon: Ship },
  { to: "/tasks", label: "Tasks", Icon: ClipboardList },
  { to: "/predictions", label: "Predictions", Icon: Waves },
  { to: "/spectral", label: "Spectral", Icon: ActivitySquare },
  { to: "/alerts", label: "Alerts", Icon: Bell },
  { to: "/admin", label: "Admin", Icon: ActivitySquare },
  { to: "/settings", label: "Settings", Icon: Settings }
];

export function AppLayout() {
  const [open, setOpen] = useState(false);
  return (
    <div className="min-h-screen bg-ink text-slate-100">
      <div className="fixed inset-x-0 top-0 z-40 border-b border-white/10 bg-ink/95 backdrop-blur lg:hidden">
        <div className="flex h-14 items-center justify-between px-4">
          <div>
            <p className="text-sm font-semibold text-white">Sargassum Sentinel</p>
            <p className="text-xs text-slate-400">Marine operations command</p>
          </div>
          <button className="rounded p-2 text-slate-200 ring-1 ring-white/10" onClick={() => setOpen((value) => !value)}>
            <Menu size={20} />
          </button>
        </div>
        {open ? (
          <nav className="grid grid-cols-3 gap-2 border-t border-white/10 p-3">
            {nav.map(({ to, label, Icon }) => (
              <NavLink
                key={to}
                to={to}
                onClick={() => setOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-2 rounded px-3 py-2 text-sm ${isActive ? "bg-cyanline/15 text-cyanline" : "text-slate-300"}`
                }
              >
                <Icon size={16} />
                {label}
              </NavLink>
            ))}
          </nav>
        ) : null}
      </div>

      <aside className="fixed bottom-0 left-0 top-0 hidden w-64 border-r border-white/10 bg-panel/95 p-5 lg:block">
        <div className="mb-8">
          <p className="text-lg font-semibold text-white">Sargassum Sentinel</p>
          <p className="mt-1 text-sm text-slate-400">Tracking, forecasting, routing</p>
        </div>
        <nav className="space-y-1">
          {nav.map(({ to, label, Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded px-3 py-2.5 text-sm transition ${isActive ? "bg-cyanline/15 text-cyanline ring-1 ring-cyanline/20" : "text-slate-300 hover:bg-white/5 hover:text-white"}`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="absolute bottom-5 left-5 right-5 rounded-lg border border-emerald-400/20 bg-emerald-500/10 p-3">
          <p className="text-xs uppercase tracking-wide text-emerald-200">System status</p>
          <p className="mt-1 text-sm text-slate-200">API-first MVP ready for live feeds</p>
        </div>
      </aside>

      <main className="px-4 pb-8 pt-20 lg:ml-64 lg:px-7 lg:pt-7">
        <Outlet />
      </main>
    </div>
  );
}

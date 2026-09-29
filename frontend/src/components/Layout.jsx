import { useEffect, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import AIChatPanel from "./AIChatPanel";
import { SeverityBadge } from "./ui";

const ICONS = {
  dashboard: "M3 3h7v7H3zM14 3h7v4h-7zM14 11h7v10h-7zM3 14h7v7H3z",
  predictions: "M4 19V9m5 10V5m5 14v-7m5 7V3",
  complaints: "M6 2h9l5 5v15H6zM14 2v6h6M9 13h8M9 17h8",
  intelligence: "M12 3a6 6 0 0 0-3.6 10.8V18h7.2v-4.2A6 6 0 0 0 12 3zM9 22h6",
  alerts: "M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4",
  graph: "M6 5h.01M18 5h.01M12 19h.01M6 5l6 14M18 5l-6 14M6 5h12",
  menu: "M4 6h16M4 12h16M4 18h16",
  close: "M6 6l12 12M18 6 6 18",
  eye: "M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12zM12 9a3 3 0 1 1 0 6 3 3 0 0 1 0-6z",
  spark: "M12 3l1.5 5.5L19 10l-5.5 1.5L12 17l-1.5-5.5L5 10l5.5-1.5z",
};

function Icon({ name, className = "h-5 w-5" }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={ICONS[name]} />
    </svg>
  );
}

const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: "dashboard" },
  { to: "/predictions", label: "Predictions", icon: "predictions" },
  { to: "/complaints", label: "Complaints", icon: "complaints" },
  { to: "/intelligence", label: "Intelligence", icon: "intelligence" },
  { to: "/alerts", label: "Alerts", icon: "alerts" },
  { to: "/graph", label: "Fraud Graph", icon: "graph", roles: ["i4c_admin", "state_lea"] },
];

const ROLE_LABEL = {
  i4c_admin: "I4C Admin",
  state_lea: "State LEA",
  bank_officer: "Bank Officer",
};

function Brand() {
  return (
    <div className="flex items-center gap-3">
      <div className="grid h-10 w-10 place-items-center border border-accent/40 bg-accent text-black shadow-[0_0_24px_rgba(132,204,22,0.14)]">
        <Icon name="eye" className="h-5 w-5" />
      </div>
      <div>
        <div className="font-mono text-lg font-bold uppercase tracking-[0.16em] text-text">VIZHI</div>
        <div className="font-mono text-[9px] font-semibold uppercase tracking-[0.22em] text-muted">Predict. Prevent. Protect.</div>
      </div>
    </div>
  );
}

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [agentOpen, setAgentOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [toast, setToast] = useState(null);
  const visibleNav = NAV.filter((item) => !item.roles || item.roles.includes(user?.role));

  useEffect(() => {
    const handler = (event) => {
      if (["INPUT", "TEXTAREA", "SELECT"].includes(event.target.tagName)) return;
      if (event.key === "a") setAgentOpen((open) => !open);
      if (event.key === "d") navigate("/dashboard");
      if (event.key === "g" && user?.role !== "bank_officer") navigate("/graph");
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [navigate, user]);

  useEffect(() => {
    const token = localStorage.getItem("vizhi_access");
    if (!token) return undefined;
    let socket;
    try {
      const protocol = location.protocol === "https:" ? "wss" : "ws";
      socket = new WebSocket(`${protocol}://${location.host}/api/ws/alerts?token=${encodeURIComponent(token)}`);
      socket.onmessage = (event) => {
        setToast(JSON.parse(event.data));
        window.setTimeout(() => setToast(null), 6000);
      };
    } catch {
      // Live push is optional; the alert timeline remains available.
    }
    return () => socket?.close();
  }, []);

  const navItems = (mobile = false) => visibleNav.map((item) => (
    <NavLink
      key={item.to}
      to={item.to}
      onClick={() => mobile && setMobileOpen(false)}
      className={({ isActive }) =>
        `group relative flex min-h-11 items-center gap-2 border px-3 py-2.5 font-mono text-xs font-semibold uppercase tracking-[0.08em] transition-colors ${
          isActive
            ? "border-accent/40 bg-accent/10 text-accent"
            : "border-transparent text-muted hover:border-white/10 hover:bg-white/5 hover:text-text"
        }`
      }
    >
      <Icon name={item.icon} className="h-4 w-4" />
      {item.label}
    </NavLink>
  ));

  return (
    <div className="tech-grid min-h-screen bg-bg text-text">
      <a href="#main-content" className="fixed left-4 top-2 z-[100] -translate-y-20 bg-accent px-4 py-2 font-mono text-xs font-bold uppercase tracking-wider text-black focus:translate-y-0">Skip to main content</a>

      <header className="sticky top-0 z-30 border-b border-white/10 bg-bg/90 backdrop-blur-xl">
        <div className="mx-auto flex min-h-[76px] max-w-[1600px] items-center gap-5 px-4 md:px-6">
          <div className="shrink-0"><Brand /></div>

          <nav className="hidden flex-1 items-center justify-center gap-1 xl:flex" aria-label="Primary navigation">
            {navItems()}
          </nav>

          <div className="ml-auto flex items-center gap-2">
            <div className="hidden border-l border-white/10 pl-4 2xl:block">
              <div className="font-mono text-[11px] font-semibold uppercase tracking-wider text-text">{user?.full_name}</div>
              <div className="font-mono text-[9px] uppercase tracking-wider text-muted">{ROLE_LABEL[user?.role]}{user?.scope_value && ` · ${user.scope_value}`}</div>
            </div>
            <button
              onClick={() => setAgentOpen(true)}
              className="inline-flex min-h-11 items-center gap-2 border border-accent bg-accent px-3.5 font-mono text-xs font-bold uppercase tracking-wider text-black transition hover:bg-accent/90"
            >
              <Icon name="spark" className="h-4 w-4" />
              <span className="hidden md:inline">Ask VIZHI</span>
            </button>
            <button
              onClick={() => { logout(); navigate("/login"); }}
              className="hidden min-h-11 border border-white/10 px-3 font-mono text-xs font-semibold uppercase tracking-wider text-muted transition hover:border-danger/40 hover:bg-danger/10 hover:text-danger xl:block"
            >
              Sign out
            </button>
            <button
              onClick={() => setMobileOpen((open) => !open)}
              className="grid h-11 w-11 place-items-center border border-white/10 text-text transition hover:border-accent/40 hover:text-accent xl:hidden"
              aria-label={mobileOpen ? "Close navigation" : "Open navigation"}
              aria-expanded={mobileOpen}
            >
              <Icon name={mobileOpen ? "close" : "menu"} />
            </button>
          </div>
        </div>

        {mobileOpen && (
          <div className="border-t border-white/10 bg-surface/95 px-4 py-4 shadow-2xl shadow-black/50 xl:hidden">
            <nav className="mx-auto grid max-w-[1600px] grid-cols-1 gap-1 sm:grid-cols-2 lg:grid-cols-3" aria-label="Mobile navigation">{navItems(true)}</nav>
            <div className="mx-auto mt-3 flex max-w-[1600px] items-center justify-between border-t border-white/10 pt-3">
              <div>
                <div className="font-mono text-xs font-semibold uppercase tracking-wider text-text">{user?.full_name}</div>
                <div className="font-mono text-[10px] uppercase tracking-wider text-muted">{ROLE_LABEL[user?.role]}{user?.scope_value && ` · ${user.scope_value}`}</div>
              </div>
              <button
                onClick={() => { logout(); navigate("/login"); }}
                className="min-h-11 border border-danger/30 px-4 font-mono text-xs font-semibold uppercase tracking-wider text-danger hover:bg-danger/10"
              >
                Sign out
              </button>
            </div>
          </div>
        )}
      </header>

      <main id="main-content" tabIndex="-1" className="mx-auto max-w-[1600px] p-4 md:p-6 lg:p-8">{children}</main>

      {agentOpen && <AIChatPanel context={{}} onClose={() => setAgentOpen(false)} />}

      {toast && (
        <div className="fixed bottom-6 right-6 z-50 max-w-sm border border-accent/30 bg-surface p-4 shadow-2xl shadow-black/50" role="status">
          <div className="mb-1 flex items-center gap-2">
            <SeverityBadge level={toast.severity} />
            <span className="font-mono text-xs font-medium uppercase tracking-wider text-muted">Live alert</span>
          </div>
          <div className="text-sm font-semibold">{toast.title}</div>
          {toast.district && <div className="text-xs text-muted">{toast.district}</div>}
        </div>
      )}
    </div>
  );
}

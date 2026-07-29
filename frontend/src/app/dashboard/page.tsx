"use client";

import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
  Lock, Wifi, WifiOff, ShieldAlert, Activity, Battery,
  Camera, AlertTriangle, TrendingUp, Users, Zap, RefreshCw,
  ChevronRight, Eye, MoreHorizontal,
} from "lucide-react";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis,
  ResponsiveContainer, Tooltip, CartesianGrid,
} from "recharts";
import { toast } from "sonner";

import { analyticsApi, lockerApi } from "@/lib/api";
import { Topbar } from "@/components/layout/Topbar";
import { cn, getBatteryColor, getThreatColor, getThreatLabel, formatRelativeTime } from "@/lib/utils";
import { useOrgSocket } from "@/hooks/useSocket";

// ── Types ──────────────────────────────────────────────────────────────────────
interface Metrics {
  total_lockers: number;
  online_lockers: number;
  offline_lockers: number;
  today_access_count: number;
  unauthorized_attempts_today: number;
  active_alerts: number;
  avg_battery: number;
  threat_score_avg: number;
  camera_online_count: number;
  network_health_percent: number;
}

// ── Animated counter ───────────────────────────────────────────────────────────
function Counter({ value, decimals = 0 }: { value: number; decimals?: number }) {
  return <span>{value.toFixed(decimals)}</span>;
}

// ── Metric Card ────────────────────────────────────────────────────────────────
function MetricCard({
  icon: Icon,
  label,
  value,
  sub,
  trend,
  color = "vault",
  delay = 0,
}: {
  icon: React.ElementType;
  label: string;
  value: React.ReactNode;
  sub?: string;
  trend?: number;
  color?: "vault" | "emerald" | "red" | "amber" | "sky";
  delay?: number;
}) {
  const colors = {
    vault:   { bg: "bg-vault-500/10",   icon: "text-vault-400",   ring: "ring-vault-500/20" },
    emerald: { bg: "bg-emerald-500/10", icon: "text-emerald-400", ring: "ring-emerald-500/20" },
    red:     { bg: "bg-red-500/10",     icon: "text-red-400",     ring: "ring-red-500/20" },
    amber:   { bg: "bg-amber-500/10",   icon: "text-amber-400",   ring: "ring-amber-500/20" },
    sky:     { bg: "bg-sky-500/10",     icon: "text-sky-400",     ring: "ring-sky-500/20" },
  };
  const c = colors[color];

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.4, ease: "easeOut" }}
      className="metric-card"
    >
      <div className="flex items-start justify-between">
        <div className={cn("flex h-10 w-10 items-center justify-center rounded-xl ring-1", c.bg, c.ring)}>
          <Icon className={cn("h-5 w-5", c.icon)} />
        </div>
        {trend !== undefined && (
          <span className={cn("flex items-center gap-1 text-xs font-medium", trend >= 0 ? "text-emerald-400" : "text-red-400")}>
            <TrendingUp className="h-3 w-3" />
            {Math.abs(trend)}%
          </span>
        )}
      </div>
      <div>
        <div className="stat-value">{value}</div>
        <div className="stat-label">{label}</div>
      </div>
      {sub && <p className="text-[11px] text-slate-600">{sub}</p>}
    </motion.div>
  );
}

// ── Event Row ──────────────────────────────────────────────────────────────────
function EventRow({ event, index }: { event: Record<string, string>; index: number }) {
  const severityStyles = {
    Critical: "badge-critical",
    Warning:  "badge-warning",
    Info:     "badge-locked",
  };
  const severity = event.severity as keyof typeof severityStyles;

  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05 }}
      className="flex items-center gap-4 py-3 border-b border-white/[0.04] last:border-0 hover:bg-white/[0.02] rounded-lg px-2 transition-colors cursor-pointer"
    >
      <div className={severityStyles[severity] ?? "badge-locked"}>
        {severity}
      </div>
      <div className="flex-1 min-w-0">
        <p className="truncate text-sm font-medium text-slate-200">{event.event_type?.replace(/([A-Z])/g, " $1").trim()}</p>
        <p className="truncate text-xs text-slate-500">{event.description}</p>
      </div>
      <span className="shrink-0 text-xs text-slate-600">{formatRelativeTime(event.timestamp)}</span>
      <ChevronRight className="h-3.5 w-3.5 text-slate-600 shrink-0" />
    </motion.div>
  );
}

// ── Locker Status Card ─────────────────────────────────────────────────────────
function LockerStatusCard({ locker, index }: { locker: Record<string, unknown>; index: number }) {
  const isOnline = locker.is_online as boolean;
  const status = locker.status as string;
  const battery = locker.battery_status as number;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay: index * 0.06 }}
      className="glass-card-hover p-4 cursor-pointer"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2.5">
          <div className={cn(
            "flex h-8 w-8 items-center justify-center rounded-lg",
            isOnline ? "bg-emerald-500/10 ring-1 ring-emerald-500/20" : "bg-slate-500/10 ring-1 ring-slate-500/20"
          )}>
            <Lock className={cn("h-4 w-4", isOnline ? "text-emerald-400" : "text-slate-500")} />
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-200">{locker.name as string}</p>
            <p className="text-xs text-slate-500">{locker.location as string ?? "No location"}</p>
          </div>
        </div>
        <button className="btn-ghost h-6 w-6 p-0">
          <MoreHorizontal className="h-3.5 w-3.5" />
        </button>
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        {isOnline ? (
          <span className="badge-online"><span className="pulse-dot-green" />Online</span>
        ) : (
          <span className="badge-offline">Offline</span>
        )}
        <span className={cn(
          "badge-locked",
          status === "Unlocked" && "badge-unlocked",
          status === "Tampered" && "badge-tampered",
        )}>
          {status}
        </span>
      </div>

      <div className="mt-3 flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <Battery className={cn("h-3.5 w-3.5", getBatteryColor(battery))} />
          <span className={cn("text-xs font-medium", getBatteryColor(battery))}>{battery}%</span>
        </div>
        <button className="flex items-center gap-1 text-xs text-vault-400 hover:text-vault-300 transition-colors">
          <Eye className="h-3 w-3" />
          View Live
        </button>
      </div>
    </motion.div>
  );
}

// ── Dashboard Page ─────────────────────────────────────────────────────────────
export default function DashboardPage() {
  const { data: metrics, refetch: refetchMetrics, isLoading: metricsLoading } = useQuery<Metrics>({
    queryKey: ["dashboard-metrics"],
    queryFn: () => analyticsApi.dashboard().then((r) => r.data),
    refetchInterval: 30_000,
  });

  const { data: accessTrend } = useQuery({
    queryKey: ["access-trend"],
    queryFn:  () => analyticsApi.accessTrend(14).then((r) => r.data),
  });

  const { data: lockers } = useQuery({
    queryKey: ["lockers"],
    queryFn:  () => lockerApi.list({ limit: 6 }).then((r) => r.data),
    refetchInterval: 30_000,
  });

  // Real-time security events via WebSocket
  const orgId = typeof window !== "undefined" ? localStorage.getItem("va_org_id") ?? "demo" : "demo";
  useOrgSocket(orgId, {
    security_event: (data) => {
      const severity = (data as Record<string, string>).severity;
      const eventType = ((data as Record<string, string>).event_type ?? "").replace(/([A-Z])/g, " $1").trim();
      if (severity === "Critical") {
        toast.error(`🚨 Critical: ${eventType}`, { duration: 8000 });
      } else if (severity === "Warning") {
        toast.warning(`⚠️ Warning: ${eventType}`);
      }
      refetchMetrics();
    },
  });

  const threatScore = metrics?.threat_score_avg ?? 0;

  // Demo events when no backend
  const demoEvents = [
    { event_type: "FingerprintFailed", severity: "Warning",  description: "Locker A1 — 3 attempts",              timestamp: new Date(Date.now() - 120000).toISOString() },
    { event_type: "MotionDetected",    severity: "Info",     description: "Locker B2 — motion after hours",       timestamp: new Date(Date.now() - 450000).toISOString() },
    { event_type: "DoorForced",        severity: "Critical", description: "Locker C3 — forced entry attempt",     timestamp: new Date(Date.now() - 900000).toISOString() },
    { event_type: "BatteryLow",        severity: "Warning",  description: "Locker A2 — battery at 12%",           timestamp: new Date(Date.now() - 1800000).toISOString() },
    { event_type: "Tampering",         severity: "Critical", description: "Locker D1 — tamper sensor triggered",  timestamp: new Date(Date.now() - 3600000).toISOString() },
  ];

  const demoAccessTrend = Array.from({ length: 14 }, (_, i) => {
    const d = new Date(); d.setDate(d.getDate() - (13 - i));
    return {
      date: d.toLocaleDateString("en", { month: "short", day: "numeric" }),
      granted: Math.floor(Math.random() * 40 + 10),
      denied:  Math.floor(Math.random() * 8),
    };
  });

  const chartData = (accessTrend as typeof demoAccessTrend) ?? demoAccessTrend;

  return (
    <div className="flex flex-col">
      <Topbar
        title="Security Dashboard"
        subtitle="Real-time monitoring & threat intelligence"
        onRefresh={refetchMetrics}
      />

      <div className="p-6 space-y-6">
        {/* ── Threat Score Banner ─────────────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card p-4 flex items-center gap-6"
        >
          <div className="flex items-center gap-3">
            <div className={cn(
              "flex h-12 w-12 items-center justify-center rounded-xl ring-1",
              threatScore < 0.3 ? "bg-emerald-500/10 ring-emerald-500/20" :
              threatScore < 0.6 ? "bg-amber-500/10 ring-amber-500/20" :
              "bg-red-500/10 ring-red-500/20"
            )}>
              <ShieldAlert className={cn("h-6 w-6", getThreatColor(threatScore))} />
            </div>
            <div>
              <p className="text-xs font-medium text-slate-500">Overall Threat Score</p>
              <p className={cn("text-3xl font-black tabular-nums", getThreatColor(threatScore))}>
                {(threatScore * 100).toFixed(0)}
                <span className="text-base font-normal text-slate-500">/100</span>
              </p>
            </div>
          </div>

          <div className="flex-1">
            <div className="h-2 rounded-full bg-white/[0.06] overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${threatScore * 100}%` }}
                transition={{ duration: 1, ease: "easeOut" }}
                className={cn(
                  "h-full rounded-full",
                  threatScore < 0.3 ? "bg-emerald-500" :
                  threatScore < 0.6 ? "bg-amber-500" : "bg-red-500"
                )}
              />
            </div>
            <p className={cn("mt-1 text-sm font-semibold", getThreatColor(threatScore))}>
              {getThreatLabel(threatScore)} Risk Level
            </p>
          </div>

          <div className="hidden md:flex items-center gap-6 text-center">
            <div>
              <p className="stat-value text-xl">{metrics?.active_alerts ?? 0}</p>
              <p className="stat-label">Active Alerts</p>
            </div>
            <div>
              <p className="stat-value text-xl">{metrics?.unauthorized_attempts_today ?? 0}</p>
              <p className="stat-label">Unauth. Today</p>
            </div>
            <div>
              <p className="stat-value text-xl">{metrics?.network_health_percent?.toFixed(0) ?? 0}%</p>
              <p className="stat-label">Network Health</p>
            </div>
          </div>
        </motion.div>

        {/* ── KPI Metrics Grid ─────────────────────────────────────────────── */}
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-5">
          <MetricCard icon={Lock}        label="Total Lockers"     value={<Counter value={metrics?.total_lockers ?? 0} />}                  color="vault"   delay={0.05} />
          <MetricCard icon={Wifi}        label="Online"            value={<Counter value={metrics?.online_lockers ?? 0} />}                  color="emerald" delay={0.10} sub={`${metrics?.offline_lockers ?? 0} offline`} />
          <MetricCard icon={Activity}    label="Today's Access"    value={<Counter value={metrics?.today_access_count ?? 0} />}              color="sky"     delay={0.15} />
          <MetricCard icon={Camera}      label="Cameras Online"    value={<Counter value={metrics?.camera_online_count ?? 0} />}             color="vault"   delay={0.20} />
          <MetricCard icon={Battery}     label="Avg Battery"       value={<><Counter value={metrics?.avg_battery ?? 0} decimals={0} />%</>}  color="amber"   delay={0.25} />
        </div>

        {/* ── Charts + Events ──────────────────────────────────────────────── */}
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
          {/* Access trend chart */}
          <div className="glass-card p-5 xl:col-span-2">
            <div className="flex items-center justify-between mb-5">
              <div>
                <h2 className="text-sm font-semibold text-slate-200">Access Trend</h2>
                <p className="text-xs text-slate-500">Last 14 days — granted vs denied</p>
              </div>
              <div className="flex items-center gap-3 text-xs text-slate-500">
                <span className="flex items-center gap-1.5"><span className="inline-block h-2 w-2 rounded-full bg-vault-500" />Granted</span>
                <span className="flex items-center gap-1.5"><span className="inline-block h-2 w-2 rounded-full bg-red-500" />Denied</span>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={chartData} margin={{ left: -16, right: 4 }}>
                <defs>
                  <linearGradient id="grantedGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#6366f1" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="deniedGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#ef4444" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip
                  contentStyle={{
                    background: "rgba(15,23,42,0.95)",
                    border: "1px solid rgba(255,255,255,0.08)",
                    borderRadius: "10px",
                    fontSize: "12px",
                    color: "#e2e8f0",
                  }}
                />
                <Area type="monotone" dataKey="granted" stroke="#6366f1" strokeWidth={2} fill="url(#grantedGrad)" />
                <Area type="monotone" dataKey="denied"  stroke="#ef4444" strokeWidth={2} fill="url(#deniedGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Recent events */}
          <div className="glass-card p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-slate-200">Recent Events</h2>
              <button className="text-xs text-vault-400 hover:text-vault-300 transition-colors">View all</button>
            </div>
            <div className="space-y-0">
              {demoEvents.map((evt, i) => (
                <EventRow key={i} event={evt} index={i} />
              ))}
            </div>
          </div>
        </div>

        {/* ── Locker Overview ──────────────────────────────────────────────── */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-slate-200">Locker Overview</h2>
            <a href="/dashboard/lockers" className="text-xs text-vault-400 hover:text-vault-300 transition-colors flex items-center gap-1">
              Manage all <ChevronRight className="h-3 w-3" />
            </a>
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {((lockers as Record<string, unknown>[]) ?? [
              { id: "1", name: "Locker A1", location: "Building 1, Floor 2", status: "Locked",    is_online: true,  battery_status: 87 },
              { id: "2", name: "Locker B2", location: "Building 2, Lobby",   status: "Unlocked",  is_online: true,  battery_status: 45 },
              { id: "3", name: "Locker C3", location: "Building 3, Floor 1", status: "Tampered",  is_online: false, battery_status: 12 },
              { id: "4", name: "Locker D1", location: "Server Room",         status: "Locked",    is_online: true,  battery_status: 95 },
              { id: "5", name: "Locker E2", location: "HR Department",       status: "Locked",    is_online: true,  battery_status: 72 },
              { id: "6", name: "Locker F3", location: "Finance Wing",        status: "Offline",   is_online: false, battery_status: 0  },
            ]).map((locker, i) => (
              <LockerStatusCard key={locker.id as string} locker={locker} index={i} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

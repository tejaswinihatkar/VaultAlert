"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Clock, ArrowLeft, ShieldAlert, AlertTriangle, Info, RefreshCw } from "lucide-react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ||
  process.env.NEXT_PUBLIC_API_URL ||
  "https://vaultalert-api.onrender.com";

interface HistoryEvent {
  id: string;
  message: string;
  event_type: string;
  severity: string; // "Critical" | "Warning" | "Info"
  photo_url: string | null;
  timestamp: string | null; // ISO
}

const SEVERITIES = ["All", "Critical", "Warning", "Info"] as const;

export default function HistoryPage() {
  const [events, setEvents] = useState<HistoryEvent[]>([]);
  const [severity, setSeverity] = useState<(typeof SEVERITIES)[number]>("All");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = async () => {
    setLoading(true);
    setError(false);
    try {
      const q = severity === "All" ? "" : `?severity=${severity}`;
      const res = await fetch(`${API_BASE}/api/v1/history${q}`);
      if (!res.ok) throw new Error("bad status");
      setEvents(await res.json());
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [severity]);

  const fmt = (iso: string | null) =>
    iso ? new Date(iso).toLocaleString() : "—";

  const sevIcon = (s: string) => {
    if (s === "Critical") return <ShieldAlert className="h-4 w-4 text-red-500" />;
    if (s === "Warning") return <AlertTriangle className="h-4 w-4 text-amber-500" />;
    return <Info className="h-4 w-4 text-slate-400" />;
  };

  // Group by day for a timestamp-wise view.
  const byDay = events.reduce<Record<string, HistoryEvent[]>>((acc, e) => {
    const day = e.timestamp ? new Date(e.timestamp).toLocaleDateString() : "Unknown";
    (acc[day] ||= []).push(e);
    return acc;
  }, {});

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans antialiased pb-12">
      <header className="sticky top-0 z-50 backdrop-blur-md bg-white/80 border-b border-slate-200 px-6 py-4 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="flex items-center gap-2 px-3 py-1.5 border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 text-xs font-semibold rounded-full transition-all"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Live Dashboard
          </Link>
          <div className="flex items-center gap-2">
            <Clock className="h-5 w-5 text-indigo-500" />
            <h1 className="text-lg font-bold tracking-tight">Alert History</h1>
          </div>
        </div>
        <button
          onClick={load}
          className="flex items-center gap-1.5 text-xs text-indigo-500 hover:text-indigo-400"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh
        </button>
      </header>

      <main className="max-w-5xl mx-auto px-6 mt-8 space-y-6">
        {/* Filter */}
        <div className="flex items-center gap-2">
          {SEVERITIES.map((s) => (
            <button
              key={s}
              onClick={() => setSeverity(s)}
              className={`px-3 py-1.5 rounded-full text-xs font-semibold border transition-all ${
                severity === s
                  ? "bg-indigo-600 text-white border-indigo-600"
                  : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
              }`}
            >
              {s}
            </button>
          ))}
          <span className="ml-auto text-xs text-slate-400">{events.length} events</span>
        </div>

        {error ? (
          <div className="rounded-2xl border border-dashed border-red-200 bg-white p-8 text-center text-sm text-slate-500">
            Could not load history. The database may be waking up — try Refresh in a few seconds.
          </div>
        ) : loading ? (
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-14 rounded-xl bg-slate-100 animate-pulse" />
            ))}
          </div>
        ) : events.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-200 bg-white p-8 text-center text-sm text-slate-400">
            No historical events yet. Alerts will be recorded here as they arrive.
          </div>
        ) : (
          Object.entries(byDay).map(([day, items]) => (
            <div key={day}>
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
                {day}
              </h3>
              <div className="space-y-2">
                {items.map((e) => (
                  <div
                    key={e.id}
                    className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-3 shadow-sm"
                  >
                    {sevIcon(e.severity)}
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-semibold text-slate-800 truncate">
                        {e.message}
                      </p>
                      <p className="text-[11px] text-slate-400">
                        {e.event_type} · {e.severity}
                      </p>
                    </div>
                    {e.photo_url && (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={e.photo_url}
                        alt="snapshot"
                        className="h-10 w-10 rounded-lg object-cover border border-slate-200"
                      />
                    )}
                    <span className="text-xs text-slate-400 whitespace-nowrap">
                      {fmt(e.timestamp)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </main>
    </div>
  );
}

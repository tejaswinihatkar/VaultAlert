"use client";
import React, { useState, useEffect } from "react";
import { Topbar } from "@/components/layout/Topbar";
import { Activity, ShieldAlert, Check, Loader2, AlertTriangle, Info, Calendar } from "lucide-react";
import { formatRelativeTime } from "@/lib/utils";
import { useEvents, useResolveEvent } from "@/hooks/useEvents";
import { useQueryClient } from "@tanstack/react-query";
import { useOrgSocket } from "@/hooks/useSocket";

export default function EventsPage() {
  const [severityFilter, setSeverityFilter] = useState("All");
  const [page, setPage] = useState(1);
  const queryClient = useQueryClient();

  // Fetch events using React Query
  const { data, isLoading } = useEvents({
    page,
    size: 20,
    severity: severityFilter === "All" ? undefined : severityFilter,
  });

  const resolveEvent = useResolveEvent();

  // Listen to live WebSocket events to automatically invalidate and refetch
  const orgId = typeof window !== "undefined" ? localStorage.getItem("va_org_id") ?? "demo" : "demo";
  useOrgSocket(orgId, {
    security_event: (data) => {
      queryClient.invalidateQueries({ queryKey: ["events"] });
    },
  });

  const handleResolve = async (id: string) => {
    await resolveEvent.mutateAsync({ eventId: id });
  };

  const getSeverityBadge = (sev: string) => {
    if (sev === "Critical") return <span className="badge-critical flex items-center gap-1"><ShieldAlert className="h-3 w-3" /> Critical</span>;
    if (sev === "Warning") return <span className="badge-warning flex items-center gap-1"><AlertTriangle className="h-3 w-3" /> Warning</span>;
    return <span className="badge-offline flex items-center gap-1"><Info className="h-3 w-3" /> Info</span>;
  };

  const events = data?.items || [];

  return (
    <div className="flex-1 flex flex-col min-h-screen">
      <Topbar title="Security Incidents" subtitle="Real-time threat monitoring and incident audit trail" />
      <main className="flex-1 p-6 space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
              <Activity className="h-5 w-5 text-vault-400" /> Security Incidents
            </h1>
            <p className="text-xs text-slate-500 mt-1">Real-time threat monitoring and incident audit trail</p>
          </div>
          <div className="flex gap-2">
            {["All", "Critical", "Warning", "Info"].map(s => (
              <button
                key={s}
                onClick={() => { setSeverityFilter(s); setPage(1); }}
                className={`py-1.5 px-3 rounded-lg text-xs font-semibold ring-1 ${severityFilter === s ? "bg-vault-500/10 text-vault-300 ring-vault-500/20" : "bg-white/3 text-slate-400 ring-white/5"}`}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        {isLoading ? (
          <div className="glass-card p-6 h-64 flex items-center justify-center text-slate-500">
            <Loader2 className="h-6 w-6 animate-spin text-vault-400" />
          </div>
        ) : events.length === 0 ? (
          <div className="glass-card p-8 text-center text-slate-500">No security incidents recorded.</div>
        ) : (
          <div className="space-y-4">
            {events.map(e => (
              <div key={e.id} className="glass-card p-5 flex flex-col md:flex-row items-start justify-between gap-4">
                <div className="space-y-2 flex-1">
                  <div className="flex items-center gap-2.5">
                    {getSeverityBadge(e.severity)}
                    <span className="text-xs text-slate-600 flex items-center gap-1">
                      <Calendar className="h-3.5 w-3.5" /> {formatRelativeTime(e.timestamp)}
                    </span>
                  </div>
                  <p className="text-sm font-semibold text-slate-200">{e.description}</p>
                  
                  {e.before_snapshot_url && (
                    <div className="mt-3 rounded-xl overflow-hidden max-w-md border border-white/10">
                      <img src={e.before_snapshot_url} alt="Captured alert snap" className="w-full h-auto object-cover" />
                    </div>
                  )}
                  
                  {e.ai_summary && (
                    <p className="text-xs text-slate-500 italic bg-white/[0.01] p-2.5 rounded-lg border border-white/[0.04]">
                      AI Summary: {e.ai_summary}
                    </p>
                  )}
                </div>

                {!e.resolved ? (
                  <button onClick={() => handleResolve(e.id)} className="btn-primary py-2 px-4 text-xs shrink-0">
                    <Check className="h-3.5 w-3.5" /> Resolve Event
                  </button>
                ) : (
                  <span className="text-xs text-emerald-400 font-semibold flex items-center gap-1.5 shrink-0">
                    ✓ Resolved
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
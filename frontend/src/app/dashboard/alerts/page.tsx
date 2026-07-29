"use client";
import React, { useState } from "react";
import { Topbar } from "@/components/layout/Topbar";
import { Bell, Trash2, ShieldAlert, AlertTriangle, Info, Check, CheckSquare } from "lucide-react";
import { formatRelativeTime } from "@/lib/utils";

interface AlertItem {
  id: string;
  title: string;
  message: string;
  severity: "Critical" | "Warning" | "Info";
  is_read: boolean;
  timestamp: string;
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<AlertItem[]>([
    { id: "1", title: "Locker Forced Open", message: "Critical breach on Vault Alpha at 18:20", severity: "Critical", is_read: false, timestamp: new Date(Date.now() - 1000 * 60 * 15).toISOString() },
    { id: "2", title: "Low Battery", message: "Vault Beta battery is at 12%. Recharging recommended.", severity: "Warning", is_read: false, timestamp: new Date(Date.now() - 1000 * 60 * 60 * 3).toISOString() },
    { id: "3", title: "System Heartbeat Restored", message: "Device ESP32-A1B2 is back online.", severity: "Info", is_read: true, timestamp: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString() },
  ]);

  const markAllRead = () => {
    setAlerts(alerts.map(a => ({ ...a, is_read: true })));
  };

  const markRead = (id: string) => {
    setAlerts(alerts.map(a => a.id === id ? { ...a, is_read: true } : a));
  };

  return (
    <div className="flex-1 flex flex-col min-h-screen">
      <Topbar title="Notifications & Alerts" subtitle="Manage system event notifications" />
      <main className="flex-1 p-6 space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
              <Bell className="h-5 w-5 text-vault-400" /> Notifications & Alerts
            </h1>
            <p className="text-xs text-slate-500 mt-1">Manage system event notifications</p>
          </div>
          <button onClick={markAllRead} className="btn-ghost text-xs flex items-center gap-1.5 hover:text-slate-200">
            <CheckSquare className="h-4 w-4" /> Mark All as Read
          </button>
        </div>

        <div className="space-y-3">
          {alerts.map(a => (
            <div
              key={a.id}
              onClick={() => markRead(a.id)}
              className={`glass-card p-5 flex items-start gap-4 transition-all duration-200 cursor-pointer ${!a.is_read ? "border-vault-500/30 bg-vault-500/[0.02]" : "opacity-70"}`}
            >
              <div className={`p-2 rounded-xl ring-1 ${a.severity === "Critical" ? "bg-red-500/10 ring-red-500/20 text-red-400" : a.severity === "Warning" ? "bg-amber-500/10 ring-amber-500/20 text-amber-400" : "bg-sky-500/10 ring-sky-500/20 text-sky-400"}`}>
                {a.severity === "Critical" ? <ShieldAlert className="h-5 w-5" /> : a.severity === "Warning" ? <AlertTriangle className="h-5 w-5" /> : <Info className="h-5 w-5" />}
              </div>
              <div className="flex-1 space-y-1">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-slate-200">{a.title}</h3>
                  <span className="text-xs text-slate-500">{formatRelativeTime(a.timestamp)}</span>
                </div>
                <p className="text-xs text-slate-400">{a.message}</p>
              </div>
              {!a.is_read && (
                <div className="h-2 w-2 rounded-full bg-vault-500 shrink-0 self-center" />
              )}
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
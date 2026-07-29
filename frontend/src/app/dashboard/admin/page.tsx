"use client";
import React, { useState } from "react";
import { Topbar } from "@/components/layout/Topbar";
import { Shield, Server, RefreshCw, Cpu, Activity } from "lucide-react";
import { toast } from "sonner";

export default function AdminPage() {
  const [services, setServices] = useState([
    { name: "FastAPI Backend Server", status: "Healthy", latency: "14ms" },
    { name: "Mosquitto MQTT Broker", status: "Healthy", latency: "5ms" },
    { name: "PostgreSQL Database", status: "Healthy", latency: "2ms" },
    { name: "Redis Cache & PubSub", status: "Healthy", latency: "1ms" },
  ]);

  const handleRestart = (name: string) => {
    toast.success(`Restart signal sent to container for ${name}`);
  };

  return (
    <div className="flex-1 flex flex-col min-h-screen">
      <Topbar title="Platform Administration" subtitle="Superuser metrics and infrastructure control panel" />
      <main className="flex-1 p-6 space-y-6 max-w-4xl">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <Shield className="h-5 w-5 text-vault-400" /> Platform Administration
          </h1>
          <p className="text-xs text-slate-500 mt-1">Superuser metrics and infrastructure control panel</p>
        </div>

        <div className="glass-card p-6 space-y-4">
          <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2">
            <Server className="h-4 w-4 text-vault-400" /> Services Health Overview
          </h2>
          <div className="space-y-3">
            {services.map((s, idx) => (
              <div key={idx} className="flex items-center justify-between p-3.5 rounded-xl border border-white/[0.04] bg-white/[0.01]">
                <div className="flex items-center gap-3">
                  <div className="h-2 w-2 rounded-full bg-emerald-500 pulse-dot-green" />
                  <div>
                    <p className="text-xs font-semibold text-slate-200">{s.name}</p>
                    <p className="text-[10px] text-slate-500 mt-0.5">Latency: {s.latency}</p>
                  </div>
                </div>
                <button onClick={() => handleRestart(s.name)} className="btn-ghost p-1.5 text-xs flex items-center gap-1 hover:text-slate-200">
                  <RefreshCw className="h-3.5 w-3.5" /> Restart
                </button>
              </div>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="glass-card p-6 space-y-4">
            <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2">
              <Cpu className="h-4 w-4 text-vault-400" /> System Resources
            </h2>
            <div className="space-y-3 text-xs text-slate-400">
              <div className="flex justify-between"><span>CPU Usage</span><span className="font-semibold text-slate-200">12.4%</span></div>
              <div className="w-full bg-white/5 h-2 rounded-full"><div className="bg-vault-500 h-full rounded-full" style={{ width: "12.4%" }}></div></div>
              <div className="flex justify-between"><span>RAM Allocated</span><span className="font-semibold text-slate-200">1.82 GB / 4.00 GB</span></div>
              <div className="w-full bg-white/5 h-2 rounded-full"><div className="bg-vault-500 h-full rounded-full" style={{ width: "45.5%" }}></div></div>
            </div>
          </div>

          <div className="glass-card p-6 space-y-4">
            <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2">
              <Activity className="h-4 w-4 text-vault-400" /> Docker Microservices
            </h2>
            <div className="space-y-3 text-xs text-slate-400">
              <div className="flex justify-between"><span>Active Containers</span><span className="font-semibold text-emerald-400">6 Containers Online</span></div>
              <div className="flex justify-between"><span>MQTT Listeners</span><span className="font-semibold text-slate-200">3 Subscribed Channels</span></div>
              <div className="flex justify-between"><span>Websocket Clients</span><span className="font-semibold text-slate-200">2 Active Connections</span></div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
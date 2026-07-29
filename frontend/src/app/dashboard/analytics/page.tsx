"use client";
import React from "react";
import { Topbar } from "@/components/layout/Topbar";
import { BarChart3, TrendingUp, ShieldAlert, Clock } from "lucide-react";
import { AreaChart, Area, BarChart as RechartsBarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid } from "recharts";

export default function AnalyticsPage() {
  const accessData = [
    { date: "Jul 10", granted: 40, denied: 4 },
    { date: "Jul 11", granted: 45, denied: 2 },
    { date: "Jul 12", granted: 38, denied: 8 },
    { date: "Jul 13", granted: 52, denied: 1 },
    { date: "Jul 14", granted: 60, denied: 5 },
    { date: "Jul 15", granted: 48, denied: 3 },
  ];

  return (
    <div className="flex-1 flex flex-col min-h-screen">
      <Topbar title="Advanced Analytics" subtitle="Audit access trends and security incidents" />
      <main className="flex-1 p-6 space-y-6">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-vault-400" /> Advanced Analytics
          </h1>
          <p className="text-xs text-slate-500 mt-1">Audit access trends and security incidents</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="glass-card p-6 space-y-4">
            <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-vault-400" /> Daily Access Trends
            </h2>
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={accessData}>
                  <defs>
                    <linearGradient id="colorGranted" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.2}/>
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Area type="monotone" dataKey="granted" stroke="#10b981" fillOpacity={1} fill="url(#colorGranted)" />
                  <Area type="monotone" dataKey="denied" stroke="#ef4444" fillOpacity={0} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="glass-card p-6 space-y-4">
            <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 text-vault-400" /> Daily Threats Logged
            </h2>
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <RechartsBarChart data={accessData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="denied" fill="#ef4444" radius={[4, 4, 0, 0]} />
                </RechartsBarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
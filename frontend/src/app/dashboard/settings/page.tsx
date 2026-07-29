"use client";
import React, { useState } from "react";
import { Topbar } from "@/components/layout/Topbar";
import { Settings, Save, Shield, Bell, HardDrive, RefreshCw } from "lucide-react";
import { toast } from "sonner";

export default function SettingsPage() {
  const [emailAlerts, setEmailAlerts] = useState(true);
  const [smsAlerts, setSmsAlerts] = useState(false);
  const [retention, setRetention] = useState(30);
  const [sensitivity, setSensitivity] = useState("Medium");

  const handleSave = () => {
    toast.success("Settings saved successfully!");
  };

  return (
    <div className="flex-1 flex flex-col min-h-screen">
      <Topbar title="Platform Settings" subtitle="Configure VaultAlert system and security preferences" />
      <main className="flex-1 p-6 space-y-6 max-w-4xl">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <Settings className="h-5 w-5 text-vault-400" /> Platform Settings
          </h1>
          <p className="text-xs text-slate-500 mt-1">Configure VaultAlert system and security preferences</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="glass-card p-6 space-y-6">
            <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2">
              <Bell className="h-4 w-4 text-vault-400" /> Notifications Configuration
            </h2>
            <div className="space-y-4">
              <label className="flex items-center justify-between cursor-pointer">
                <div>
                  <p className="text-xs font-semibold text-slate-300">Email Notifications</p>
                  <p className="text-[10px] text-slate-500 mt-0.5">Critical breach alerts to workspace emails</p>
                </div>
                <input
                  type="checkbox"
                  checked={emailAlerts}
                  onChange={e => setEmailAlerts(e.target.checked)}
                  className="rounded bg-slate-900 border-white/10 text-vault-500 focus:ring-vault-500/20"
                />
              </label>

              <label className="flex items-center justify-between cursor-pointer">
                <div>
                  <p className="text-xs font-semibold text-slate-300">SMS / Twilio Alerts</p>
                  <p className="text-[10px] text-slate-500 mt-0.5">Instant phone text updates for critical warnings</p>
                </div>
                <input
                  type="checkbox"
                  checked={smsAlerts}
                  onChange={e => setSmsAlerts(e.target.checked)}
                  className="rounded bg-slate-900 border-white/10 text-vault-500 focus:ring-vault-500/20"
                />
              </label>
            </div>
          </div>

          <div className="glass-card p-6 space-y-6">
            <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2">
              <Shield className="h-4 w-4 text-vault-400" /> Sensor Sensitivity
            </h2>
            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="stat-label">Motion Trigger Level</label>
                <select
                  value={sensitivity}
                  onChange={e => setSensitivity(e.target.value)}
                  className="vault-input"
                >
                  <option value="Low">Low (Reduce false alarms)</option>
                  <option value="Medium">Medium (Balanced)</option>
                  <option value="High">High (High security zones)</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="stat-label">Cloud Video Retention (Days)</label>
                <input
                  type="number"
                  value={retention}
                  onChange={e => setRetention(parseInt(e.target.value))}
                  className="vault-input"
                />
              </div>
            </div>
          </div>
        </div>

        <div className="flex justify-end pt-4">
          <button onClick={handleSave} className="btn-primary py-2.5 px-6">
            <Save className="h-4 w-4" /> Save Configuration
          </button>
        </div>
      </main>
    </div>
  );
}
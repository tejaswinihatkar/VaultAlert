"use client";
import React, { useState } from "react";
import { Topbar } from "@/components/layout/Topbar";
import { Shield, Key, Plus, Trash2, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";

interface Permission {
  id: string;
  user_name: string;
  locker_name: string;
  can_unlock: boolean;
  can_view_live: boolean;
}

export default function AccessControlPage() {
  const [permissions, setPermissions] = useState<Permission[]>([
    { id: "1", user_name: "John Doe", locker_name: "Vault Alpha", can_unlock: true, can_view_live: true },
    { id: "2", user_name: "Sarah Connor", locker_name: "Vault Beta", can_unlock: true, can_view_live: true },
  ]);

  const handleRevoke = (id: string) => {
    setPermissions(permissions.filter(p => p.id !== id));
    toast.success("Access permission revoked successfully.");
  };

  return (
    <div className="flex-1 flex flex-col min-h-screen">
      <Topbar title="Access Authorization Matrix" subtitle="Configure and audit who can lock or unlock specific storage vaults" />
      <main className="flex-1 p-6 space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
              <Key className="h-5 w-5 text-vault-400" /> Access Authorization Matrix
            </h1>
            <p className="text-xs text-slate-500 mt-1">Configure and audit who can lock or unlock specific storage vaults</p>
          </div>
          <button onClick={() => toast.info("Permission granting model coming soon")} className="btn-primary">
            <Plus className="h-4 w-4" /> Grant Access
          </button>
        </div>

        <div className="glass-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-white/[0.06] bg-white/[0.01]">
                  <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-500">Authorized User</th>
                  <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-500">Locker / Vault</th>
                  <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-500">Remote Unlock</th>
                  <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-500">Live Camera</th>
                  <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-500">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {permissions.map(p => (
                  <tr key={p.id} className="transition-colors hover:bg-white/[0.02]">
                    <td className="px-6 py-4 text-sm font-semibold text-slate-300">{p.user_name}</td>
                    <td className="px-6 py-4 text-sm text-slate-400">{p.locker_name}</td>
                    <td className="px-6 py-4 text-sm">
                      <span className="badge-online flex items-center gap-1 w-max"><CheckCircle2 className="h-3.5 w-3.5" /> Allowed</span>
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <span className="badge-online flex items-center gap-1 w-max"><CheckCircle2 className="h-3.5 w-3.5" /> Allowed</span>
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <button onClick={() => handleRevoke(p.id)} className="btn-ghost p-1.5 rounded-lg text-red-500 hover:text-red-400" title="Revoke Permission">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
}
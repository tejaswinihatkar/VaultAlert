"use client";
import React, { useState } from "react";
import { Topbar } from "@/components/layout/Topbar";
import { Users, UserPlus, Shield, Mail, Trash2, Edit } from "lucide-react";
import { toast } from "sonner";

interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: string;
  status: "Active" | "Deactivated";
}

export default function UsersPage() {
  const [members, setMembers] = useState<TeamMember[]>([
    { id: "1", name: "Tejas S", email: "admin@vaultalert.io", role: "Admin", status: "Active" },
    { id: "2", name: "Sarah Connor", email: "connor@vaultalert.io", role: "Manager", status: "Active" },
    { id: "3", name: "John Doe", email: "doe@vaultalert.io", role: "Employee", status: "Active" },
  ]);

  const handleDeactivate = (id: string) => {
    setMembers(members.map(m => m.id === id ? { ...m, status: m.status === "Active" ? "Deactivated" : "Active" } : m));
    toast.success("User status toggled successfully.");
  };

  return (
    <div className="flex-1 flex flex-col min-h-screen">
      <Topbar title="Team Management" subtitle="Invite and manage organization users & roles" />
      <main className="flex-1 p-6 space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
              <Users className="h-5 w-5 text-vault-400" /> Team Management
            </h1>
            <p className="text-xs text-slate-500 mt-1">Invite and manage organization users & roles</p>
          </div>
          <button onClick={() => toast.info("Invite modal coming soon")} className="btn-primary">
            <UserPlus className="h-4 w-4" /> Invite User
          </button>
        </div>

        <div className="glass-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-white/[0.06] bg-white/[0.01]">
                  <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-500">Name</th>
                  <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-500">Email</th>
                  <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-500">Role</th>
                  <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-500">Status</th>
                  <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-500">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {members.map(m => (
                  <tr key={m.id} className="transition-colors hover:bg-white/[0.02]">
                    <td className="px-6 py-4 text-sm font-semibold text-slate-300">{m.name}</td>
                    <td className="px-6 py-4 text-sm text-slate-400">{m.email}</td>
                    <td className="px-6 py-4 text-sm">
                      <span className="badge-locked">{m.role}</span>
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <span className={m.status === "Active" ? "badge-online" : "badge-offline"}>{m.status}</span>
                    </td>
                    <td className="px-6 py-4 text-sm flex gap-2">
                      <button onClick={() => handleDeactivate(m.id)} className="btn-ghost p-1.5 rounded-lg text-xs text-slate-400 hover:text-red-400">
                        {m.status === "Active" ? "Deactivate" : "Activate"}
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
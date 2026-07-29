"use client";
import React, { useState } from "react";
import { useLockers, useCreateLocker, useDeleteLocker, useLockerControl } from "@/hooks/useLockers";
import { Topbar } from "@/components/layout/Topbar";
import { DataTable, Column } from "@/components/ui/DataTable";
import { Modal } from "@/components/ui/Modal";
import { EmptyState } from "@/components/ui/EmptyState";
import { Lock, Unlock, ShieldAlert, Plus, Search, Trash2, Battery, Wifi, MapPin } from "lucide-react";
import { Locker, LockerStatus } from "@/types";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

export default function LockersPage() {
  const { data: lockers = [], isLoading } = useLockers();
  const createLocker = useCreateLocker();
  const deleteLocker = useDeleteLocker();
  const control = useLockerControl();

  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState("");
  const { register, handleSubmit, reset } = useForm();

  const handleCreate = async (data: any) => {
    await createLocker.mutateAsync({
      name: data.name,
      locker_number: data.locker_number || undefined,
      location: data.location || undefined,
      gps_lat: data.gps_lat ? parseFloat(data.gps_lat) : undefined,
      gps_lng: data.gps_lng ? parseFloat(data.gps_lng) : undefined,
    });
    setIsOpen(false);
    reset();
  };

  const getStatusBadge = (status: LockerStatus) => {
    const badges = {
      Locked: "badge-locked",
      Unlocked: "badge-unlocked",
      Tampered: "badge-tampered",
      Offline: "badge-offline",
      Lockdown: "badge-critical",
    };
    return <span className={badges[status] || "badge-offline"}>{status}</span>;
  };

  const filtered = lockers.filter(l => l.name.toLowerCase().includes(search.toLowerCase()));

  const columns: Column<Locker>[] = [
    { key: "name", label: "Locker Name" },
    { key: "locker_number", label: "Locker #" },
    { key: "location", label: "Location", render: (_, row) => (
      <span className="flex items-center gap-1"><MapPin className="h-3.5 w-3.5 text-slate-500" /> {row.location || "N/A"}</span>
    )},
    { key: "status", label: "Status", render: (_, row) => getStatusBadge(row.status) },
    { key: "battery", label: "Battery", render: (_, row) => (
      <span className="flex items-center gap-1.5"><Battery className="h-4 w-4 text-emerald-400" /> {row.battery_status}%</span>
    )},
    { key: "signal", label: "Signal", render: (_, row) => (
      <span className="flex items-center gap-1.5"><Wifi className="h-4 w-4 text-sky-400" /> {row.signal_strength} dBm</span>
    )},
    { key: "actions", label: "Actions", render: (_, row) => (
      <div className="flex gap-2" onClick={e => e.stopPropagation()}>
        <button
          onClick={() => control.mutate({ id: row.id, action: row.status === "Locked" ? "unlock" : "lock" })}
          className="btn-ghost p-1.5 rounded-lg"
          title={row.status === "Locked" ? "Unlock" : "Lock"}
        >
          {row.status === "Locked" ? <Unlock className="h-4 w-4 text-emerald-400" /> : <Lock className="h-4 w-4 text-slate-400" />}
        </button>
        <button
          onClick={() => control.mutate({ id: row.id, action: "lockdown" })}
          className="btn-ghost p-1.5 rounded-lg text-red-500 hover:text-red-400"
          title="Emergency Lockdown"
        >
          <ShieldAlert className="h-4 w-4" />
        </button>
        <button
          onClick={() => { if(confirm("Are you sure?")) deleteLocker.mutate(row.id); }}
          className="btn-ghost p-1.5 rounded-lg text-slate-500 hover:text-red-400"
          title="Delete"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
    )}
  ];

  return (
    <div className="flex-1 flex flex-col min-h-screen">
      <Topbar title="Locker Management" subtitle="Register and monitor device locks" />
      <main className="flex-1 p-6 space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
              <Lock className="h-5 w-5 text-vault-400" /> Locker Management
            </h1>
            <p className="text-xs text-slate-500 mt-1">Register and monitor device locks</p>
          </div>
          <button onClick={() => setIsOpen(true)} className="btn-primary">
            <Plus className="h-4 w-4" /> Add Locker
          </button>
        </div>

        <div className="flex gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Search lockers..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="vault-input pl-10"
            />
          </div>
        </div>

        {isLoading ? (
          <div className="glass-card p-6 h-64 flex items-center justify-center text-slate-500">Loading...</div>
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={Lock}
            title="No Lockers Registered"
            description="Add your first smart locker to monitor real-time telemetry."
            action={{ label: "Add Locker", onClick: () => setIsOpen(true) }}
          />
        ) : (
          <DataTable columns={columns} data={filtered} />
        )}
      </main>

      <Modal isOpen={isOpen} onClose={() => setIsOpen(false)} title="Register New Locker">
        <form onSubmit={handleSubmit(handleCreate)} className="space-y-4">
          <div className="space-y-1.5">
            <label className="stat-label">Locker Name</label>
            <input {...register("name", { required: true })} placeholder="Main Safe" className="vault-input" />
          </div>
          <div className="space-y-1.5">
            <label className="stat-label">Locker Number</label>
            <input {...register("locker_number")} placeholder="VAULT-A1" className="vault-input" />
          </div>
          <div className="space-y-1.5">
            <label className="stat-label">Location (Building / Floor)</label>
            <input {...register("location")} placeholder="HQ - 2nd Floor Server Room" className="vault-input" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="stat-label">GPS Latitude</label>
              <input {...register("gps_lat")} placeholder="37.7749" className="vault-input" />
            </div>
            <div className="space-y-1.5">
              <label className="stat-label">GPS Longitude</label>
              <input {...register("gps_lng")} placeholder="-122.4194" className="vault-input" />
            </div>
          </div>
          <button type="submit" className="btn-primary w-full py-3">Register Device</button>
        </form>
      </Modal>
    </div>
  );
}
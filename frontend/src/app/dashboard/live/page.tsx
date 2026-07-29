"use client";
import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Topbar } from "@/components/layout/Topbar";
import { lockerApi } from "@/lib/api";
import { Lock, Camera, ArrowRight, Eye, Video } from "lucide-react";
import { useRouter } from "next/navigation";
import { Locker } from "@/types";
import { EmptyState } from "@/components/ui/EmptyState";
import { cn } from "@/lib/utils";

export default function LiveMonitorSelectorPage() {
  const router = useRouter();

  const { data: lockers = [], isLoading } = useQuery<Locker[]>({
    queryKey: ["lockers-list"],
    queryFn: () => lockerApi.list().then((r) => r.data),
  });

  return (
    <div className="flex-1 flex flex-col min-h-screen">
      <Topbar title="Live Monitor Feed" subtitle="Select a security locker to view live camera feed" />
      <main className="flex-1 p-6 space-y-6">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <Camera className="h-5 w-5 text-vault-400" /> Live Surveillance Feed
          </h1>
          <p className="text-xs text-slate-500 mt-1">Select a smart locker to view live camera snapshots & telemetry</p>
        </div>

        {isLoading ? (
          <div className="glass-card p-6 h-64 flex items-center justify-center text-slate-500">
            Loading camera feeds...
          </div>
        ) : lockers.length === 0 ? (
          <EmptyState
            icon={Camera}
            title="No Cameras Available"
            description="Register a smart locker with camera capabilities to view surveillance feeds."
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {lockers.map((locker) => (
              <div
                key={locker.id}
                onClick={() => router.push(`/dashboard/live/${locker.id}`)}
                className="glass-card-hover p-5 cursor-pointer flex flex-col justify-between h-44"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <div className="p-2 rounded-xl bg-vault-500/10 text-vault-400">
                      <Video className="h-5 w-5" />
                    </div>
                    <span className={locker.is_online ? "badge-online" : "badge-offline"}>
                      {locker.is_online ? "Device Online" : "Offline"}
                    </span>
                  </div>
                  <h3 className="text-sm font-semibold text-slate-200">{locker.name}</h3>
                  <p className="text-xs text-slate-500 mt-1">{locker.location || "No location set"}</p>
                </div>
                <div className="flex items-center justify-between text-xs text-vault-400 font-semibold pt-4 border-t border-white/[0.04] mt-3">
                  <span className="flex items-center gap-1"><Eye className="h-3.5 w-3.5" /> View Feed</span>
                  <ArrowRight className="h-4 w-4" />
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

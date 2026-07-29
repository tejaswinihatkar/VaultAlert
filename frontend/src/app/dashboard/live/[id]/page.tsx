"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  Lock, Unlock, ShieldAlert, Camera, Wifi, Battery,
  Thermometer, Droplets, Activity, AlertTriangle,
  RefreshCw, PowerOff, Settings, ZapOff,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { lockerApi } from "@/lib/api";
import { Topbar } from "@/components/layout/Topbar";
import { useLockerSocket } from "@/hooks/useSocket";
import { cn, getBatteryColor, getThreatColor, getSignalStrength } from "@/lib/utils";

type TelemetryState = {
  battery: number; signal: number; temperature: number; humidity: number;
  door_status: string; tamper: boolean; motion: boolean;
};

export default function LiveLockerPage() {
  const { id } = useParams<{ id: string }>();
  const [telemetry, setTelemetry] = useState<Partial<TelemetryState>>({});
  const [issuingCommand, setIssuingCommand] = useState<string | null>(null);
  const [recentEvents, setRecentEvents] = useState<Record<string, string>[]>([]);

  const { data: locker, refetch } = useQuery({
    queryKey: ["locker", id],
    queryFn: () => lockerApi.get(id).then((r) => r.data),
    enabled: !!id,
    refetchInterval: 60_000,
  });

  // Live telemetry & events from WebSocket
  useLockerSocket(id, {
    telemetry_update: (data) => {
      setTelemetry((prev) => ({ ...prev, ...(data as Partial<TelemetryState>) }));
    },
    security_event: (data) => {
      const evt = data as Record<string, string>;
      setRecentEvents((prev) => [evt, ...prev.slice(0, 9)]);
      if (evt.severity === "Critical") {
        toast.error(`🚨 ${evt.event_type?.replace(/([A-Z])/g, " $1").trim()} detected!`, { duration: 10000 });
      } else if (evt.severity === "Warning") {
        toast.warning(`⚠️ ${evt.event_type?.replace(/([A-Z])/g, " $1").trim()}`);
      }
    },
    device_offline: () => toast.error("🔴 Device went offline"),
    device_online:  () => toast.success("🟢 Device is back online"),
  });

  const battery    = telemetry.battery    ?? locker?.battery_status  ?? 0;
  const signal     = telemetry.signal     ?? locker?.signal_strength ?? -70;
  const temp       = telemetry.temperature ?? locker?.temperature    ?? 0;
  const humidity   = telemetry.humidity   ?? locker?.humidity        ?? 0;
  const doorStatus = telemetry.door_status ?? locker?.door_state     ?? "Closed";
  const tamper     = telemetry.tamper      ?? locker?.tamper_detected ?? false;
  const motion     = telemetry.motion      ?? locker?.motion_detected ?? false;

  const issueCommand = async (cmd: "unlock" | "lock" | "lockdown") => {
    setIssuingCommand(cmd);
    try {
      const fn = { unlock: lockerApi.unlock, lock: lockerApi.lock, lockdown: lockerApi.lockdown }[cmd];
      await fn(id);
      toast.success(`${cmd.charAt(0).toUpperCase() + cmd.slice(1)} command sent`);
      refetch();
    } catch {
      toast.error(`Failed to issue ${cmd} command`);
    } finally {
      setIssuingCommand(null);
    }
  };

  return (
    <div className="flex flex-col">
      <Topbar
        title={locker?.name ?? "Live Locker"}
        subtitle={locker?.location ?? "Loading…"}
        onRefresh={refetch}
      />

      <div className="p-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
        {/* ── Camera Feed ────────────────────────────────────────────────── */}
        <div className="xl:col-span-2 space-y-4">
          <div className="glass-card overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06]">
              <div className="flex items-center gap-2">
                <span className="pulse-dot-red" />
                <span className="text-sm font-semibold text-slate-200">Live Camera Feed</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="badge-online text-xs">LIVE</span>
                <Camera className="h-4 w-4 text-slate-500" />
              </div>
            </div>
            {/* Camera placeholder — replace with actual RTSP/WebRTC stream */}
            <div className="relative aspect-video bg-surface-950 flex items-center justify-center">
              <div className="absolute inset-0 bg-[linear-gradient(rgba(99,102,241,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(99,102,241,0.02)_1px,transparent_1px)] bg-[size:32px_32px]" />
              <div className="text-center">
                <Camera className="h-12 w-12 text-slate-700 mx-auto mb-3" />
                <p className="text-sm text-slate-600">Camera stream active</p>
                <p className="text-xs text-slate-700">Connect RTSP/WebRTC source to display live feed</p>
              </div>
              {/* Overlay indicators */}
              {tamper && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="absolute inset-0 border-2 border-red-500/50 pointer-events-none flex items-center justify-center"
                >
                  <div className="bg-red-500/90 rounded-lg px-4 py-2">
                    <p className="text-sm font-bold text-white">⚠ TAMPER DETECTED</p>
                  </div>
                </motion.div>
              )}
              {motion && !tamper && (
                <div className="absolute top-3 right-3 badge-warning">
                  <Activity className="h-3 w-3" />Motion
                </div>
              )}
            </div>
          </div>

          {/* Recent Events Feed */}
          <div className="glass-card p-4">
            <h3 className="text-sm font-semibold text-slate-200 mb-3">Live Event Feed</h3>
            {recentEvents.length === 0 ? (
              <p className="text-xs text-slate-600 py-4 text-center">No events yet. Monitoring active…</p>
            ) : (
              <div className="space-y-2">
                {recentEvents.map((evt, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="flex items-center gap-3 rounded-lg bg-white/[0.02] px-3 py-2"
                  >
                    <span className={cn(
                      "h-1.5 w-1.5 rounded-full shrink-0",
                      evt.severity === "Critical" ? "bg-red-500" :
                      evt.severity === "Warning"  ? "bg-amber-500" : "bg-blue-500"
                    )} />
                    <span className="text-xs font-medium text-slate-300">
                      {evt.event_type?.replace(/([A-Z])/g, " $1").trim()}
                    </span>
                    <span className="text-xs text-slate-600 ml-auto">{evt.timestamp?.split("T")[1]?.slice(0, 8)}</span>
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ── Control Panel ───────────────────────────────────────────────── */}
        <div className="space-y-4">
          {/* Locker Status */}
          <div className="glass-card p-5">
            <h3 className="section-title mb-4">Locker Status</h3>
            <div className="space-y-3">
              {[
                { label: "Door State",   value: doorStatus,                       icon: Lock,         color: doorStatus === "Open" ? "text-amber-400" : "text-emerald-400" },
                { label: "Lock Status",  value: locker?.status ?? "Unknown",      icon: ShieldAlert,  color: locker?.status === "Locked" ? "text-emerald-400" : "text-red-400" },
                { label: "Tamper",       value: tamper ? "DETECTED" : "Normal",   icon: AlertTriangle, color: tamper ? "text-red-400" : "text-slate-500" },
                { label: "Motion",       value: motion ? "Detected" : "Clear",    icon: Activity,     color: motion ? "text-amber-400" : "text-slate-500" },
              ].map((item) => (
                <div key={item.label} className="flex items-center justify-between py-2 border-b border-white/[0.04] last:border-0">
                  <div className="flex items-center gap-2 text-slate-500">
                    <item.icon className="h-3.5 w-3.5" />
                    <span className="text-xs">{item.label}</span>
                  </div>
                  <span className={cn("text-xs font-semibold", item.color)}>{item.value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Telemetry */}
          <div className="glass-card p-5">
            <h3 className="section-title mb-4">Device Telemetry</h3>
            <div className="grid grid-cols-2 gap-3">
              {[
                { icon: Battery,     label: "Battery",     value: `${battery}%`,              color: getBatteryColor(battery) },
                { icon: Wifi,        label: "Signal",      value: getSignalStrength(signal),  color: "text-sky-400" },
                { icon: Thermometer, label: "Temperature", value: `${temp?.toFixed(1)}°C`,   color: "text-orange-400" },
                { icon: Droplets,    label: "Humidity",    value: `${humidity?.toFixed(0)}%`, color: "text-blue-400" },
              ].map((item) => (
                <div key={item.label} className="rounded-xl bg-white/[0.03] p-3 ring-1 ring-white/[0.05]">
                  <item.icon className={cn("h-4 w-4 mb-2", item.color)} />
                  <p className={cn("text-sm font-bold", item.color)}>{item.value}</p>
                  <p className="text-[10px] text-slate-600 mt-0.5">{item.label}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Remote Controls */}
          <div className="glass-card p-5">
            <h3 className="section-title mb-4">Remote Control</h3>
            <div className="space-y-2.5">
              <button
                onClick={() => issueCommand("unlock")}
                disabled={issuingCommand !== null}
                className="btn-primary w-full"
              >
                {issuingCommand === "unlock" ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Unlock className="h-4 w-4" />}
                Unlock Locker
              </button>
              <button
                onClick={() => issueCommand("lock")}
                disabled={issuingCommand !== null}
                className="btn-ghost w-full ring-1 ring-white/10"
              >
                {issuingCommand === "lock" ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Lock className="h-4 w-4" />}
                Lock Locker
              </button>
              <button
                onClick={() => issueCommand("lockdown")}
                disabled={issuingCommand !== null}
                className="btn-danger w-full"
              >
                {issuingCommand === "lockdown" ? <RefreshCw className="h-4 w-4 animate-spin" /> : <ZapOff className="h-4 w-4" />}
                Emergency Lockdown
              </button>
            </div>
          </div>

          {/* Device Info */}
          <div className="glass-card p-5">
            <h3 className="section-title mb-3">Device Info</h3>
            <div className="space-y-2 text-xs">
              {[
                { label: "Firmware",    value: locker?.device?.firmware_version ?? "1.0.0" },
                { label: "Serial",      value: locker?.device?.serial_number    ?? "—" },
                { label: "Last Seen",   value: locker?.last_seen ? new Date(locker.last_seen).toLocaleTimeString() : "—" },
                { label: "Camera",      value: locker?.camera_online ? "Online" : "Offline" },
              ].map((item) => (
                <div key={item.label} className="flex justify-between">
                  <span className="text-slate-600">{item.label}</span>
                  <span className="font-medium text-slate-300">{item.value as string}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

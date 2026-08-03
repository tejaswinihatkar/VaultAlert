"use client";

import { useEffect, useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
  Lock,
  Unlock,
  ShieldAlert,
  Users,
  Camera,
  Activity,
  AlertTriangle,
  RefreshCw,
  Clock,
  UserCheck,
  CheckCircle,
  AlertCircle,
  Wifi,
  WifiOff,
} from "lucide-react";

// Config - read from env or default to standard values
const NTFY_TOPIC = process.env.NEXT_PUBLIC_NTFY_TOPIC || "vaultalert-mia-x9f2k7";
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

interface RawNtfyMessage {
  id: string;
  time: number; // Unix timestamp in seconds
  message: string;
}

interface ClassifiedEvent {
  id: string;
  timestamp: number; // milliseconds
  originalMessage: string;
  type: string;
  label: string;
  severity: "critical" | "high" | "info" | "success";
  name?: string;
}

interface TelegramPhoto {
  file_id: string;
  url: string;
  caption: string;
  date: number; // Unix timestamp in seconds
}

// Classifier function for the hardware events
function classifyEvent(raw: RawNtfyMessage): ClassifiedEvent {
  const msg = raw.message.trim();
  const timestamp = raw.time * 1000;

  if (msg.startsWith("Authorized:")) {
    const name = msg.replace("Authorized:", "").trim();
    return {
      id: raw.id,
      timestamp,
      originalMessage: raw.message,
      type: "authorized",
      label: "Authorized Access",
      severity: "success",
      name,
    };
  }
  if (msg === "Unauthorized fingerprint!") {
    return {
      id: raw.id,
      timestamp,
      originalMessage: raw.message,
      type: "unauthorized_fingerprint",
      label: "Unauthorized Fingerprint",
      severity: "critical",
    };
  }
  if (msg === "Wrong password attempt!") {
    return {
      id: raw.id,
      timestamp,
      originalMessage: raw.message,
      type: "wrong_password",
      label: "Wrong PIN Attempt",
      severity: "high",
    };
  }
  if (msg === "System Locked!") {
    return {
      id: raw.id,
      timestamp,
      originalMessage: raw.message,
      type: "system_locked",
      label: "System Locked",
      severity: "critical",
    };
  }
  if (msg === "Access Granted!" || msg === "Locker Opened!") {
    return {
      id: raw.id,
      timestamp,
      originalMessage: raw.message,
      type: "access_granted",
      label: "Locker Opened",
      severity: "success",
    };
  }
  if (msg === "VaultAlert boot test") {
    return {
      id: raw.id,
      timestamp,
      originalMessage: raw.message,
      type: "boot_test",
      label: "System Boot Test",
      severity: "info",
    };
  }

  // Fallback for general messages
  return {
    id: raw.id,
    timestamp,
    originalMessage: raw.message,
    type: "unknown",
    label: msg,
    severity: "info",
  };
}

export default function DashboardPage() {
  const [events, setEvents] = useState<ClassifiedEvent[]>([]);
  const [sseConnected, setSseConnected] = useState(false);
  const [now, setNow] = useState(Date.now());

  // Tick relative timestamps every second
  useEffect(() => {
    const interval = setInterval(() => {
      setNow(Date.now());
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  // Fetch footage from the local FastAPI service
  const {
    data: footage = [],
    isLoading: isFootageLoading,
    isError: isFootageError,
    refetch: refetchFootage,
  } = useQuery<TelegramPhoto[]>({
    queryKey: ["footage"],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/api/v1/footage`);
      if (!response.ok) {
        throw new Error("Footage service unavailable");
      }
      return response.json();
    },
    refetchInterval: 10000, // Poll every 10s
    retry: false,
  });

  // Connect to ntfy.sh and Telegram to pull backlog + live messages
  useEffect(() => {
    let active = true;

    async function loadBacklog() {
      // 1. Fetch ntfy backlog
      let ntfyEvents: ClassifiedEvent[] = [];
      try {
        const response = await fetch(`https://ntfy.sh/${NTFY_TOPIC}/json?poll=1`);
        if (response.ok) {
          const text = await response.text();
          const lines = text.trim().split("\n");
          for (const line of lines) {
            if (!line) continue;
            try {
              const rawMsg: RawNtfyMessage = JSON.parse(line);
              ntfyEvents.push(classifyEvent(rawMsg));
            } catch (e) {}
          }
        }
      } catch (err) {
        console.error("Failed to load ntfy backlog:", err);
      }

      // 2. Fetch Telegram channel backlog via our backend
      let telegramEvents: ClassifiedEvent[] = [];
      try {
        const response = await fetch(`${API_BASE}/api/v1/telegram-events`);
        if (response.ok) {
          const data = await response.json();
          telegramEvents = data.map((item: any) => {
            const rawMsg: RawNtfyMessage = {
              id: item.id,
              time: item.time,
              message: item.message,
            };
            return classifyEvent(rawMsg);
          });
        }
      } catch (err) {
        console.error("Failed to load Telegram events:", err);
      }

      if (!active) return;

      // Merge and deduplicate (by checking combination of message text and timestamp, or ID)
      setEvents((prev) => {
        const combined = [...ntfyEvents, ...telegramEvents, ...prev];
        const unique = Array.from(
          new Map(combined.map((item) => [`${item.originalMessage}-${item.timestamp}`, item])).values()
        );
        return unique.sort((a, b) => b.timestamp - a.timestamp);
      });
    }

    loadBacklog();

    // Start EventSource for live updates
    const eventSource = new EventSource(`https://ntfy.sh/${NTFY_TOPIC}/sse`);

    eventSource.onopen = () => {
      if (active) setSseConnected(true);
    };

    eventSource.onerror = () => {
      if (active) setSseConnected(false);
    };

    eventSource.onmessage = (event) => {
      if (!active) return;
      try {
        const rawMsg: RawNtfyMessage = JSON.parse(event.data);
        const newEvent = classifyEvent(rawMsg);
        setEvents((prev) => {
          const combined = [newEvent, ...prev];
          const unique = Array.from(
            new Map(combined.map((item) => [`${item.originalMessage}-${item.timestamp}`, item])).values()
          );
          return unique.sort((a, b) => b.timestamp - a.timestamp);
        });
      } catch (e) {
        console.error("Failed to parse live event:", e);
      }
    };

    return () => {
      active = false;
      eventSource.close();
    };
  }, []);

  // Compute Locker State
  // Flips state to "Unlocked" if the last state-flipping event is Access Granted / Locker Opened.
  const lockerState = useMemo(() => {
    // Find the latest state-affecting message
    const stateEvent = events.find(
      (e) =>
        e.type === "access_granted" ||
        e.type === "unauthorized_fingerprint" ||
        e.type === "wrong_password" ||
        e.type === "system_locked" ||
        e.type === "boot_test"
    );

    if (!stateEvent) return "Locked";
    if (stateEvent.type === "access_granted") return "Unlocked";
    return "Locked"; // Reset to Locked on boot or alert security threats
  }, [events]);

  // Compute Authorized Users List
  const authorizedUsers = useMemo(() => {
    const userMap: { [name: string]: number } = {};
    // Chronological order processing so the latest wins
    [...events].reverse().forEach((e) => {
      if (e.type === "authorized" && e.name) {
        userMap[e.name] = e.timestamp;
      }
    });

    return Object.entries(userMap)
      .map(([name, timestamp]) => ({ name, timestamp }))
      .sort((a, b) => b.timestamp - a.timestamp);
  }, [events]);

  // Compute Active Alerts (unauthorised access, wrong PIN, lockout)
  const activeAlerts = useMemo(() => {
    return events.filter(
      (e) =>
        e.type === "unauthorized_fingerprint" ||
        e.type === "wrong_password" ||
        e.type === "system_locked"
    );
  }, [events]);

  // Format relative time helper
  const getRelativeTimeStr = (timestamp: number) => {
    const diffSec = Math.floor((now - timestamp) / 1000);
    if (diffSec < 5) return "Just now";
    if (diffSec < 60) return `${diffSec}s ago`;
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHr = Math.floor(diffMin / 60);
    return `${diffHr}h ago`;
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans antialiased pb-12 selection:bg-indigo-500 selection:text-white">
      {/* Glow effects */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-indigo-500/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute top-1/3 right-1/4 w-96 h-96 bg-emerald-500/5 rounded-full blur-[150px] pointer-events-none" />

      {/* Header */}
      <header className="sticky top-0 z-50 backdrop-blur-md bg-slate-950/80 border-b border-slate-900 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/20 ring-1 ring-white/10">
            <Lock className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent">
              VaultAlert
            </h1>
            <p className="text-xs text-slate-500">Live Hardware Security Hub</p>
          </div>
        </div>

        {/* Live status pill */}
        <div className="flex items-center gap-3">
          <div
            className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold border transition-all duration-300 ${
              sseConnected
                ? "bg-emerald-950/40 border-emerald-800/40 text-emerald-400"
                : "bg-amber-950/40 border-amber-800/40 text-amber-400"
            }`}
          >
            <span
              className={`h-2 w-2 rounded-full ${
                sseConnected ? "bg-emerald-400 animate-pulse" : "bg-amber-400"
              }`}
            />
            {sseConnected ? "Live Connection" : "Connecting..."}
          </div>
        </div>
      </header>

      {/* Dashboard Grid */}
      <main className="max-w-7xl mx-auto px-6 mt-8 space-y-8">
        
        {/* Top Hero: Locker Status & KPIs */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Hero Locker Card */}
          <div className="lg:col-span-2 relative overflow-hidden rounded-3xl border border-slate-900 bg-gradient-to-br from-slate-900 to-slate-950 p-8 flex flex-col justify-between min-h-[300px]">
            <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/5 rounded-full blur-[80px] pointer-events-none" />
            
            <div className="flex items-start justify-between">
              <div>
                <span className="text-xs font-semibold tracking-wider text-slate-500 uppercase">
                  Locker Status
                </span>
                <h2 className="text-3xl font-black mt-1 tracking-tight text-white">
                  Main Vault 01
                </h2>
              </div>
              <div className="text-right">
                <span className="text-xs text-slate-500 block">Security Factors</span>
                <span className="text-xs font-medium text-indigo-400">
                  Fingerprint · 4-digit PIN
                </span>
              </div>
            </div>

            <div className="my-8 flex items-center gap-6">
              <div
                className={`h-20 w-20 rounded-2xl flex items-center justify-center transition-all duration-500 shadow-xl ${
                  lockerState === "Unlocked"
                    ? "bg-emerald-500/10 text-emerald-400 ring-2 ring-emerald-500/20 shadow-emerald-500/10"
                    : "bg-indigo-500/10 text-indigo-400 ring-2 ring-indigo-500/20 shadow-indigo-500/10"
                }`}
              >
                {lockerState === "Unlocked" ? (
                  <Unlock className="h-10 w-10 animate-bounce" />
                ) : (
                  <Lock className="h-10 w-10" />
                )}
              </div>
              <div>
                <div
                  className={`text-4xl font-extrabold tracking-tight ${
                    lockerState === "Unlocked" ? "text-emerald-400" : "text-slate-100"
                  }`}
                >
                  {lockerState}
                </div>
                <p className="text-sm text-slate-500 mt-1">
                  {events[0] ? (
                    <>
                      Last activity:{" "}
                      <span className="text-slate-300 font-medium">
                        {events[0].label}
                      </span>{" "}
                      ({getRelativeTimeStr(events[0].timestamp)})
                    </>
                  ) : (
                    "Waiting for telemetry..."
                  )}
                </p>
              </div>
            </div>

            <div className="border-t border-slate-900 pt-4 flex items-center justify-between text-xs text-slate-500">
              <span>Hardware bus: <code className="text-indigo-400">ntfy.sh/{NTFY_TOPIC}</code></span>
              <span className="flex items-center gap-1">
                <Clock className="h-3.5 w-3.5 text-slate-600" />
                Auto-updating
              </span>
            </div>
          </div>

          {/* Stat Strip / Quick Metrics */}
          <div className="grid grid-cols-1 gap-4">
            
            {/* Active Alerts Count */}
            <div className="rounded-2xl border border-slate-900 bg-slate-900/40 p-6 flex items-center justify-between">
              <div>
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Active Alerts
                </span>
                <div className="text-3xl font-extrabold mt-1 text-slate-100">
                  {activeAlerts.length}
                </div>
              </div>
              <div className={`h-12 w-12 rounded-xl flex items-center justify-center ${
                activeAlerts.length > 0 ? "bg-red-500/10 text-red-400" : "bg-slate-800 text-slate-500"
              }`}>
                <ShieldAlert className="h-6 w-6" />
              </div>
            </div>

            {/* Authorised Users Count */}
            <div className="rounded-2xl border border-slate-900 bg-slate-900/40 p-6 flex items-center justify-between">
              <div>
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Authorised Users
                </span>
                <div className="text-3xl font-extrabold mt-1 text-slate-100">
                  {authorizedUsers.length}
                </div>
              </div>
              <div className="h-12 w-12 rounded-xl bg-slate-800 text-slate-300 flex items-center justify-center">
                <Users className="h-6 w-6" />
              </div>
            </div>

            {/* Total Events Captured */}
            <div className="rounded-2xl border border-slate-900 bg-slate-900/40 p-6 flex items-center justify-between">
              <div>
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Events Handled
                </span>
                <div className="text-3xl font-extrabold mt-1 text-slate-100">
                  {events.length}
                </div>
              </div>
              <div className="h-12 w-12 rounded-xl bg-slate-800 text-slate-300 flex items-center justify-center">
                <Activity className="h-6 w-6" />
              </div>
            </div>

          </div>
        </div>

        {/* Real-time Alerts Panel */}
        <div>
          <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-500" />
            Security Incidents
          </h3>
          {activeAlerts.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-900 p-8 text-center text-slate-500">
              No recent security alerts. Platform secure.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <AnimatePresence>
                {activeAlerts.map((alert) => (
                  <motion.div
                    key={alert.id}
                    initial={{ opacity: 0, scale: 0.95, y: 10 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    className={`rounded-2xl border p-5 flex flex-col justify-between ${
                      alert.severity === "critical"
                        ? "bg-red-950/20 border-red-900/50 text-red-100"
                        : "bg-amber-950/20 border-amber-900/50 text-amber-100"
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between mb-3">
                        <span
                          className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full ${
                            alert.severity === "critical"
                              ? "bg-red-500/20 text-red-400"
                              : "bg-amber-500/20 text-amber-400"
                          }`}
                        >
                          {alert.severity}
                        </span>
                        <span className="text-xs text-slate-500">
                          {getRelativeTimeStr(alert.timestamp)}
                        </span>
                      </div>
                      <h4 className="text-base font-bold mb-1">{alert.label}</h4>
                      <p className="text-xs text-slate-400">{alert.originalMessage}</p>
                    </div>

                    <div className="mt-4 pt-3 border-t border-white/[0.04] text-[10px] text-slate-500 flex items-center gap-1.5">
                      <CheckCircle className="h-3.5 w-3.5 text-indigo-400" />
                      Alert broadcasted to Telegram bot
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          )}
        </div>

        {/* Activity & Users Splits */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Activity Timeline */}
          <div className="lg:col-span-2 rounded-2xl border border-slate-900 bg-slate-900/20 p-6">
            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-6 flex items-center gap-2">
              <Activity className="h-4 w-4 text-indigo-400" />
              Live Activity Timeline
            </h3>

            {events.length === 0 ? (
              <div className="text-center py-12 text-slate-600 text-sm">
                Awaiting hardware connection...
              </div>
            ) : (
              <div className="relative border-l border-slate-900 ml-3.5 pl-6 space-y-6">
                {events.map((event) => {
                  let iconColor = "bg-slate-800 text-slate-400";
                  if (event.severity === "critical") {
                    iconColor = "bg-red-500/10 text-red-400 ring-1 ring-red-500/20";
                  } else if (event.severity === "high") {
                    iconColor = "bg-amber-500/10 text-amber-400 ring-1 ring-amber-500/20";
                  } else if (event.severity === "success") {
                    iconColor = "bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/20";
                  }

                  return (
                    <div key={event.id} className="relative group">
                      {/* Timeline dot */}
                      <span className={`absolute -left-[35px] top-1 h-6.5 w-6.5 rounded-full flex items-center justify-center p-1 z-10 ${iconColor}`}>
                        {event.severity === "critical" && <AlertCircle className="h-3.5 w-3.5" />}
                        {event.severity === "high" && <AlertTriangle className="h-3.5 w-3.5" />}
                        {event.severity === "success" && <UserCheck className="h-3.5 w-3.5" />}
                        {event.severity === "info" && <Clock className="h-3.5 w-3.5" />}
                      </span>

                      <div>
                        <div className="flex items-center justify-between">
                          <p className="text-sm font-bold text-slate-200">
                            {event.label}
                          </p>
                          <span className="text-xs text-slate-500">
                            {getRelativeTimeStr(event.timestamp)}
                          </span>
                        </div>
                        <p className="text-xs text-slate-400 mt-1">
                          {event.originalMessage}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Authorised Users List */}
          <div className="rounded-2xl border border-slate-900 bg-slate-900/20 p-6">
            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-6 flex items-center gap-2">
              <UserCheck className="h-4 w-4 text-emerald-400" />
              Verified Users
            </h3>

            {authorizedUsers.length === 0 ? (
              <div className="text-center py-12 text-slate-600 text-sm">
                No users verified in this session.
              </div>
            ) : (
              <div className="space-y-4">
                {authorizedUsers.map((user) => (
                  <div
                    key={user.name}
                    className="flex items-center gap-3 p-3 rounded-xl bg-slate-900/40 border border-slate-900 hover:border-slate-800 transition-colors"
                  >
                    <div className="h-8 w-8 rounded-lg bg-gradient-to-tr from-emerald-500/20 to-teal-500/20 text-emerald-400 font-bold text-xs flex items-center justify-center">
                      {user.name.slice(0, 2).toUpperCase()}
                    </div>
                    <div>
                      <p className="text-sm font-bold text-slate-200">{user.name}</p>
                      <p className="text-[10px] text-slate-500">
                        Last access: {getRelativeTimeStr(user.timestamp)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footage Section */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
              <Camera className="h-4 w-4 text-indigo-400" />
              Live Security Footage
            </h3>
            <button
              onClick={() => refetchFootage()}
              className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 transition-colors"
            >
              <RefreshCw className="h-3 w-3" />
              Sync
            </button>
          </div>

          {isFootageError ? (
            <div className="rounded-2xl border border-dashed border-red-900/30 bg-red-950/5 p-8 text-center text-slate-500">
              <WifiOff className="h-8 w-8 mx-auto mb-2 text-red-500" />
              <p className="text-sm font-semibold text-slate-300">Footage Service Offline</p>
              <p className="text-xs text-slate-500 mt-0.5">
                The standalone service is unavailable or Telegram bot credentials are missing.
              </p>
            </div>
          ) : isFootageLoading ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[...Array(4)].map((_, i) => (
                <div
                  key={i}
                  className="aspect-square rounded-2xl bg-slate-900/60 animate-pulse border border-slate-900"
                />
              ))}
            </div>
          ) : footage.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-900 p-8 text-center text-slate-500">
              No snapshot footage found. Capture events will stream here automatically.
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {footage.map((item) => (
                <div
                  key={item.file_id}
                  className="group relative aspect-square rounded-2xl overflow-hidden bg-slate-900 border border-slate-900 hover:border-slate-800 transition-all duration-300"
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={item.url}
                    alt={item.caption}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-transparent to-transparent opacity-90 p-4 flex flex-col justify-end">
                    <p className="text-xs font-bold text-slate-100 truncate">
                      {item.caption}
                    </p>
                    <p className="text-[10px] text-slate-500 mt-0.5">
                      {getRelativeTimeStr(item.date * 1000)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

      </main>
    </div>
  );
}

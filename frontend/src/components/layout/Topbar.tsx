"use client";

import { Bell, Search, RefreshCw } from "lucide-react";
import { motion } from "framer-motion";
import { useState } from "react";

interface TopbarProps {
  title: string;
  subtitle?: string;
  onRefresh?: () => void;
}

export function Topbar({ title, subtitle, onRefresh }: TopbarProps) {
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    onRefresh?.();
    setTimeout(() => setIsRefreshing(false), 1000);
  };

  return (
    <header className="flex h-16 items-center gap-4 border-b border-white/[0.06] bg-surface-900/60 backdrop-blur-xl px-6">
      {/* Page title */}
      <div className="flex-1">
        <h1 className="text-base font-semibold text-slate-100">{title}</h1>
        {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
      </div>

      {/* Search */}
      <div className="relative hidden md:block">
        <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
        <input
          type="text"
          placeholder="Search lockers, events…"
          className="vault-input h-8 w-56 pl-8 text-xs"
        />
      </div>

      {/* Refresh */}
      {onRefresh && (
        <button
          onClick={handleRefresh}
          className="btn-ghost h-8 w-8 p-0"
          aria-label="Refresh"
        >
          <motion.div animate={{ rotate: isRefreshing ? 360 : 0 }} transition={{ duration: 0.8 }}>
            <RefreshCw className="h-4 w-4" />
          </motion.div>
        </button>
      )}

      {/* Notifications */}
      <button className="relative btn-ghost h-8 w-8 p-0" aria-label="Notifications">
        <Bell className="h-4 w-4" />
        <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-red-500" />
      </button>

      {/* Time */}
      <div className="hidden lg:block text-right">
        <p className="text-xs font-medium text-slate-300">{new Date().toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" })}</p>
        <p className="text-[10px] text-slate-500">Local Time</p>
      </div>
    </header>
  );
}

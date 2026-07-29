"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import {
  LayoutDashboard, Lock, Camera, Bell, BarChart3,
  Settings, Shield, Users, FileText, Zap, LogOut,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navGroups = [
  {
    label: "Overview",
    items: [
      { href: "/dashboard",           icon: LayoutDashboard, label: "Dashboard" },
      { href: "/dashboard/lockers",   icon: Lock,            label: "Lockers" },
      { href: "/dashboard/live",      icon: Camera,          label: "Live Monitor" },
    ],
  },
  {
    label: "Security",
    items: [
      { href: "/dashboard/events",    icon: Zap,             label: "Events" },
      { href: "/dashboard/alerts",    icon: Bell,            label: "Alerts" },
      { href: "/dashboard/access",    icon: Shield,          label: "Access Control" },
    ],
  },
  {
    label: "Management",
    items: [
      { href: "/dashboard/users",     icon: Users,           label: "Users" },
      { href: "/dashboard/analytics", icon: BarChart3,       label: "Analytics" },
      { href: "/dashboard/reports",   icon: FileText,        label: "Reports" },
    ],
  },
  {
    label: "System",
    items: [
      { href: "/dashboard/settings",  icon: Settings,        label: "Settings" },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-screen w-64 flex-col border-r border-white/[0.06] bg-surface-900/80 backdrop-blur-xl">
      {/* Logo */}
      <div className="flex items-center gap-3 border-b border-white/[0.06] px-5 py-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-vault-500/20 ring-1 ring-vault-500/30">
          <Shield className="h-5 w-5 text-vault-400" />
        </div>
        <div>
          <span className="text-base font-bold tracking-tight text-slate-100">VaultAlert</span>
          <p className="text-[10px] font-medium text-slate-500">Security Platform</p>
        </div>
      </div>

      {/* Live indicator */}
      <div className="mx-4 mt-4 flex items-center gap-2 rounded-xl bg-emerald-500/5 px-3 py-2.5 ring-1 ring-emerald-500/15">
        <span className="pulse-dot-green" />
        <span className="text-xs font-medium text-emerald-400">System Online</span>
        <span className="ml-auto text-[10px] text-slate-500">v1.0.0</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-6">
        {navGroups.map((group) => (
          <div key={group.label}>
            <p className="section-title mb-2 px-3">{group.label}</p>
            <ul className="space-y-0.5">
              {group.items.map((item) => {
                const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      className={cn(
                        isActive ? "nav-item-active" : "nav-item",
                        "group relative"
                      )}
                    >
                      <item.icon className="h-4 w-4 shrink-0" />
                      <span className="flex-1">{item.label}</span>
                      {isActive && (
                        <motion.div
                          layoutId="sidebar-active"
                          className="absolute inset-0 rounded-xl bg-vault-500/10 ring-1 ring-vault-500/20"
                          transition={{ type: "spring", bounce: 0.2, duration: 0.4 }}
                        />
                      )}
                      {!isActive && (
                        <ChevronRight className="h-3 w-3 opacity-0 transition-opacity group-hover:opacity-40" />
                      )}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* User footer */}
      <div className="border-t border-white/[0.06] p-4">
        <div className="flex items-center gap-3 rounded-xl p-2 hover:bg-white/[0.04] transition-colors cursor-pointer">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-vault-500/20 text-xs font-bold text-vault-300">
            AD
          </div>
          <div className="flex-1 min-w-0">
            <p className="truncate text-xs font-semibold text-slate-200">Admin User</p>
            <p className="truncate text-[10px] text-slate-500">admin@vaultalert.io</p>
          </div>
          <LogOut className="h-4 w-4 text-slate-600 hover:text-red-400 transition-colors cursor-pointer" />
        </div>
      </div>
    </aside>
  );
}

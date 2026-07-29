"use client";
import React, { useState } from "react";
import { Topbar } from "@/components/layout/Topbar";
import { FileText, Download, FileSpreadsheet, FileArchive, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { reportsApi } from "@/lib/api";

export default function ReportsPage() {
  const [downloading, setDownloading] = useState<string | null>(null);

  const triggerDownload = async (type: string) => {
    setDownloading(type);
    try {
      let res;
      if (type === "incident") res = await reportsApi.incident();
      else if (type === "access") res = await reportsApi.accessLogs();
      else res = await reportsApi.audit();

      const blob = new Blob([res.data], { type: res.headers["content-type"] });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `vaultalert_${type}_report.${type === "access" ? "csv" : "pdf"}`);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
      toast.success("Report downloaded successfully");
    } catch {
      // Create a fallback mock download if the backend is not running or fails
      const mockContent = "Date,Locker Name,User,Action\n2026-07-16 18:00:00,Vault Alpha,John Doe,Unlocked\n";
      const blob = new Blob([mockContent], { type: "text/csv" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `vaultalert_${type}_mock_report.csv`);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
      toast.success("Downloaded simulation report (Mock fallback)");
    } finally {
      setDownloading(null);
    }
  };

  return (
    <div className="flex-1 flex flex-col min-h-screen">
      <Topbar title="Security Reports & Exports" subtitle="Export access logs and audit history" />
      <main className="flex-1 p-6 space-y-6 max-w-4xl">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <FileText className="h-5 w-5 text-vault-400" /> Security Reports & Exports
          </h1>
          <p className="text-xs text-slate-500 mt-1">Export access logs and audit history</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="glass-card p-6 flex flex-col justify-between h-48">
            <div className="space-y-2">
              <div className="p-2 w-max rounded-xl bg-red-500/10 text-red-400">
                <FileArchive className="h-6 w-6" />
              </div>
              <h3 className="text-sm font-semibold text-slate-200">Incident Reports</h3>
              <p className="text-[10px] text-slate-500">Overview of all logged threats and resolutions</p>
            </div>
            <button
              onClick={() => triggerDownload("incident")}
              disabled={downloading !== null}
              className="btn-primary py-2 text-xs flex items-center justify-center gap-1.5"
            >
              {downloading === "incident" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
              Export PDF
            </button>
          </div>

          <div className="glass-card p-6 flex flex-col justify-between h-48">
            <div className="space-y-2">
              <div className="p-2 w-max rounded-xl bg-emerald-500/10 text-emerald-400">
                <FileSpreadsheet className="h-6 w-6" />
              </div>
              <h3 className="text-sm font-semibold text-slate-200">Access Logs</h3>
              <p className="text-[10px] text-slate-500">CSV formatted audit trail of unlock operations</p>
            </div>
            <button
              onClick={() => triggerDownload("access")}
              disabled={downloading !== null}
              className="btn-primary py-2 text-xs flex items-center justify-center gap-1.5"
            >
              {downloading === "access" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
              Export CSV
            </button>
          </div>

          <div className="glass-card p-6 flex flex-col justify-between h-48">
            <div className="space-y-2">
              <div className="p-2 w-max rounded-xl bg-sky-500/10 text-sky-400">
                <FileText className="h-6 w-6" />
              </div>
              <h3 className="text-sm font-semibold text-slate-200">System Audit Trail</h3>
              <p className="text-[10px] text-slate-500">Immutable developer and admin action log</p>
            </div>
            <button
              onClick={() => triggerDownload("audit")}
              disabled={downloading !== null}
              className="btn-primary py-2 text-xs flex items-center justify-center gap-1.5"
            >
              {downloading === "audit" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
              Export PDF
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
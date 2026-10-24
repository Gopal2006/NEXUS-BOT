"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Toast } from "@/components/Toast";
import { CardSkeleton } from "@/components/Skeleton";
import { PageHeader } from "@/components/ui/PageHeader";
import { MasterCard } from "@/components/ui/MasterCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { History, User, Clock, Terminal } from "lucide-react";

export default function AuditPage() {
  const params = useParams();
  const guildId = params.guildId as string;

  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<{ type: "success" | "error"; message: string } | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const res = await fetch(`/api/backend/guilds/${guildId}/audit`);
        if (res.ok) setLogs(await res.json());
      } catch {
        setToast({ type: "error", message: "Failed to load dashboard audit records" });
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [guildId]);

  if (loading) {
    return (
      <div className="space-y-6 pb-24">
        <CardSkeleton />
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-200 pb-28 font-sans">
      {toast && (
        <Toast
          type={toast.type}
          message={toast.message}
          onClose={() => setToast(null)}
        />
      )}

      {/* Header */}
      <PageHeader
        icon={<History className="w-5 h-5 text-[var(--ice-silver)]" />}
        title="Dashboard Audit Logs"
        description="Chronological log of administrative actions, config changes, and moderation updates performed via this dashboard."
      />

      {/* Master Card with Audit Table */}
      <MasterCard
        label="ACTIVITY LOG"
        title={`Dashboard Events (${logs.length})`}
        description="Every modification committed in this panel is recorded with the operator's Discord user ID."
      >
        {logs.length === 0 ? (
          <EmptyState
            icon={<History className="w-8 h-8 text-[var(--hint)]" />}
            title="No Dashboard Records"
            description="No administrative modifications have been recorded for this server yet."
          />
        ) : (
          <div className="overflow-x-auto pt-2">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-[var(--glass-border)] text-[var(--text-faint)] uppercase tracking-wider font-mono text-[11px]">
                  <th className="py-3 px-3">Action</th>
                  <th className="py-3 px-3">Actor (User ID)</th>
                  <th className="py-3 px-3">Details / Changed Data</th>
                  <th className="py-3 px-3">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--glass-border)]">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-[var(--glass-bg-strong)]/30 transition-colors">
                    <td className="py-3.5 px-3">
                      <span className="px-2.5 py-1 rounded-md glass-soft border border-[var(--glass-border)] text-[var(--ice-silver)] font-bold text-[11px] font-mono">
                        {log.action}
                      </span>
                    </td>
                    <td className="py-3.5 px-3 font-mono text-[var(--text-muted)]">
                      {log.user_id}
                    </td>
                    <td className="py-3.5 px-3 font-mono text-[var(--ice-silver)] max-w-md truncate" title={log.details}>
                      {log.details || "—"}
                    </td>
                    <td className="py-3.5 px-3 text-[var(--text-muted)] whitespace-nowrap font-mono text-[11px]">
                      {new Date(log.timestamp * 1000).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </MasterCard>
    </div>
  );
}

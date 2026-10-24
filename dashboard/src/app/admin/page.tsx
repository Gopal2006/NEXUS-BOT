"use client";

import React, { useEffect, useState } from "react";
import { Toast } from "@/components/Toast";
import { CardSkeleton } from "@/components/Skeleton";
import { BackgroundAurora } from "@/components/BackgroundAurora";
import { FloatingTopBar } from "@/components/FloatingTopBar";
import { PageHeader } from "@/components/ui/PageHeader";
import { MasterCard } from "@/components/ui/MasterCard";
import { CountUp } from "@/components/ui/CountUp";
import { EmptyState } from "@/components/ui/EmptyState";
import { stripEmojis } from "@/lib/utils";
import { ShieldCheck, Server, Users, Cpu, Activity, UserPlus, Trash2, Key, ShieldAlert } from "lucide-react";

export default function AdminPage() {
  const [stats, setStats] = useState<any>(null);
  const [guilds, setGuilds] = useState<any[]>([]);
  const [nonPrefix, setNonPrefix] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [newNpUserId, setNewNpUserId] = useState("");
  const [toast, setToast] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const [statsRes, guildsRes, npRes] = await Promise.all([
        fetch("/api/backend/stats"),
        fetch("/api/backend/admin/guilds"),
        fetch("/api/backend/admin/nonprefix"),
      ]);

      if (statsRes.ok) setStats(await statsRes.json());
      if (guildsRes.ok) setGuilds(await guildsRes.json());
      if (npRes.ok) setNonPrefix(await npRes.json());
    } catch {
      setToast({ type: "error", message: "Failed to load admin telemetry" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleAddNp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newNpUserId.trim()) return;

    try {
      setActionLoading(true);
      const res = await fetch("/api/backend/admin/nonprefix", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: newNpUserId.trim() }),
      });

      if (!res.ok) throw new Error("Failed to add non-prefix user");

      setToast({ type: "success", message: "User granted non-prefix execution rights!" });
      setNewNpUserId("");
      await loadData();
    } catch (err: any) {
      setToast({ type: "error", message: err.message || "Failed to add" });
    } finally {
      setActionLoading(false);
    }
  };

  const handleRemoveNp = async (userId: number) => {
    try {
      setActionLoading(true);
      const res = await fetch(`/api/backend/admin/nonprefix/${userId}`, {
        method: "DELETE",
      });

      if (!res.ok) throw new Error("Failed to revoke non-prefix access");

      setToast({ type: "success", message: "Non-prefix permission revoked" });
      setNonPrefix((prev) => prev.filter((u) => u.user_id !== userId));
    } catch (err: any) {
      setToast({ type: "error", message: err.message || "Failed to remove" });
    } finally {
      setActionLoading(false);
    }
  };

  const cleanName = (name: string) => stripEmojis(name) || name;

  return (
    <div className="min-h-screen bg-[var(--bg-deep)] text-[var(--ice-silver)] font-sans relative overflow-x-hidden">
      <BackgroundAurora />
      <FloatingTopBar />

      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8 relative z-10 space-y-8 pb-28">
        {toast && (
          <Toast
            type={toast.type}
            message={toast.message}
            onClose={() => setToast(null)}
          />
        )}

        <PageHeader
          icon={<ShieldAlert className="w-5 h-5 text-[var(--warning)]" />}
          title="Global Bot Administration"
          description="Restricted to bot creators in OWNER_IDS. Live cluster telemetry, non-prefix permissions, and cluster guild directory."
        />

        {/* Global Cluster Stats */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="glass rounded-2xl p-5 relative overflow-hidden">
              <div className="sheen" />
              <div className="text-xs text-[var(--text-faint)] font-mono uppercase tracking-wider flex items-center gap-1.5">
                <Server className="w-4 h-4 text-[var(--hint)]" />
                <span>Total Guilds</span>
              </div>
              <div className="text-2xl font-bold font-display text-[var(--ice-silver)] mt-1">
                <CountUp end={stats.guilds_count || 0} />
              </div>
            </div>

            <div className="glass rounded-2xl p-5 relative overflow-hidden">
              <div className="sheen" />
              <div className="text-xs text-[var(--text-faint)] font-mono uppercase tracking-wider flex items-center gap-1.5">
                <Users className="w-4 h-4 text-[var(--success)]" />
                <span>Audience Reach</span>
              </div>
              <div className="text-2xl font-bold font-display text-[var(--ice-silver)] mt-1">
                <CountUp end={stats.users_count || 0} />
              </div>
            </div>

            <div className="glass rounded-2xl p-5 relative overflow-hidden">
              <div className="sheen" />
              <div className="text-xs text-[var(--text-faint)] font-mono uppercase tracking-wider flex items-center gap-1.5">
                <Activity className="w-4 h-4 text-[var(--warning)]" />
                <span>Gateway Latency</span>
              </div>
              <div className="text-2xl font-bold font-display text-[var(--ice-silver)] mt-1">
                <CountUp end={stats.ping_ms || 0} suffix=" ms" />
              </div>
            </div>

            <div className="glass rounded-2xl p-5 relative overflow-hidden">
              <div className="sheen" />
              <div className="text-xs text-[var(--text-faint)] font-mono uppercase tracking-wider flex items-center gap-1.5">
                <Cpu className="w-4 h-4 text-[var(--hint)]" />
                <span>Memory (RSS)</span>
              </div>
              <div className="text-2xl font-bold font-display text-[var(--ice-silver)] mt-1">
                {stats.ram_usage_mb > 0 ? `${stats.ram_usage_mb} MB` : "Active"}
              </div>
            </div>
          </div>
        )}

        {/* Non-Prefix Management */}
        <MasterCard
          label="ACCESS OVERRIDE"
          title="Non-Prefix Allowlist"
          description="Users in this allowlist can execute prefix commands without typing n! / N!."
        >
          <form onSubmit={handleAddNp} className="flex gap-3 pb-4">
            <input
              type="text"
              placeholder="Enter Discord User ID to authorize..."
              value={newNpUserId}
              onChange={(e) => setNewNpUserId(e.target.value)}
              className="flex-1 h-11 px-3.5 glass-soft border border-[var(--glass-border)] rounded-xl text-xs font-mono text-[var(--ice-silver)] focus:outline-none focus:border-[var(--ice-silver)]/50"
            />
            <button
              type="submit"
              disabled={actionLoading}
              className="px-5 py-2.5 bg-[var(--ice-silver)] text-[var(--ink)] font-mono text-xs font-bold uppercase tracking-wider rounded-xl hover:opacity-90 transition-all flex items-center gap-1.5 shrink-0 cursor-pointer shadow-md disabled:opacity-40"
            >
              <UserPlus className="w-3.5 h-3.5" />
              <span>Grant Non-Prefix</span>
            </button>
          </form>

          {nonPrefix.length === 0 ? (
            <div className="text-center py-6 text-[var(--text-muted)] text-xs">
              No users on non-prefix allowlist.
            </div>
          ) : (
            <div className="space-y-2 pt-2">
              {nonPrefix.map((np) => (
                <div
                  key={np.user_id}
                  className="p-3.5 glass-soft border border-[var(--glass-border)] rounded-xl flex items-center justify-between"
                >
                  <div className="space-y-0.5">
                    <div className="font-mono text-xs font-bold text-[var(--ice-silver)]">{np.user_id}</div>
                    <div className="text-[11px] text-[var(--text-muted)] font-mono">
                      Added by: {np.added_by || "Owner"} • {new Date(np.added_at * 1000).toLocaleDateString()}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleRemoveNp(np.user_id)}
                    disabled={actionLoading}
                    className="p-2 rounded-lg text-[var(--error)] hover:bg-[var(--error)]/10 transition-colors cursor-pointer"
                    title="Revoke access"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </MasterCard>

        {/* Global Guilds Directory */}
        <MasterCard
          label="NETWORK REACH"
          title={`Active Server Clusters (${guilds.length})`}
          description="Global servers hosting NEXUS bot instances."
        >
          {guilds.length === 0 ? (
            <div className="text-center py-6 text-[var(--text-muted)] text-xs">
              No servers connected.
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 pt-2">
              {guilds.map((g) => {
                const displayName = cleanName(g.name);
                return (
                  <div
                    key={g.id}
                    className="p-3.5 rounded-xl glass-soft border border-[var(--glass-border)] flex items-center gap-3 transition-all hover:border-[var(--ice-silver)]/20"
                  >
                    {g.icon ? (
                      <img src={g.icon} alt={displayName} className="w-10 h-10 rounded-xl object-cover border border-[var(--glass-border)] shrink-0" />
                    ) : (
                      <div className="w-10 h-10 rounded-xl glass border border-[var(--glass-border)] text-[var(--ice-silver)] font-bold flex items-center justify-center text-xs shrink-0">
                        {displayName.slice(0, 2).toUpperCase()}
                      </div>
                    )}
                    <div className="min-w-0 flex-1">
                      <div className="font-semibold text-[var(--ice-silver)] text-xs truncate">{displayName}</div>
                      <div className="text-[11px] text-[var(--text-muted)] font-mono">
                        {g.member_count.toLocaleString()} members
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </MasterCard>
      </main>
    </div>
  );
}

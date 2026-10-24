"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ChannelSelect, Channel } from "@/components/ChannelSelect";
import { RoleSelect, Role } from "@/components/RoleSelect";
import { Toast } from "@/components/Toast";
import { CardSkeleton } from "@/components/Skeleton";
import { PageHeader } from "@/components/ui/PageHeader";
import { MasterCard } from "@/components/ui/MasterCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { Gift, Sparkles, Send, Clock, Users, Trophy } from "lucide-react";

export default function GiveawaysPage() {
  const params = useParams();
  const guildId = params.guildId as string;

  const [giveaways, setGiveaways] = useState<any[]>([]);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [guildInfo, setGuildInfo] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [toast, setToast] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Giveaway form state
  const [targetChannelId, setTargetChannelId] = useState<string | null>(null);
  const [prize, setPrize] = useState("Discord Nitro (1 Month)");
  const [winners, setWinners] = useState(1);
  const [durationMinutes, setDurationMinutes] = useState(60);
  const [requiredRoleId, setRequiredRoleId] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const [gRes, chRes, roRes, guildRes] = await Promise.all([
        fetch(`/api/backend/guilds/${guildId}/giveaways`),
        fetch(`/api/backend/guilds/${guildId}/channels`),
        fetch(`/api/backend/guilds/${guildId}/roles`),
        fetch(`/api/backend/guilds/${guildId}`),
      ]);

      if (gRes.ok) setGiveaways(await gRes.json());
      if (chRes.ok) {
        const chData: Channel[] = await chRes.json();
        setChannels(chData);
        const preferred = chData.find(c => c.type === "text" && (c.name.includes("giveaway") || c.name.includes("gift") || c.name.includes("general"))) || chData.find(c => c.type === "text");
        if (preferred) setTargetChannelId(preferred.id);
      }
      if (roRes.ok) setRoles(await roRes.json());
      if (guildRes.ok) setGuildInfo(await guildRes.json());
    } catch {
      setToast({ type: "error", message: "Failed to load giveaways" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [guildId]);

  const handleStartGiveaway = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetChannelId) {
      setToast({ type: "error", message: "Please select a channel for the giveaway" });
      return;
    }
    if (!prize.trim()) {
      setToast({ type: "error", message: "Prize description cannot be empty" });
      return;
    }

    try {
      setSubmitting(true);
      const res = await fetch(`/api/backend/guilds/${guildId}/giveaways/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          channel_id: targetChannelId,
          prize: prize.trim(),
          winners: winners,
          duration_minutes: durationMinutes,
          required_role_id: requiredRoleId || undefined,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || data.error || "Failed to start giveaway");
      }

      setToast({
        type: "success",
        message: `Giveaway successfully launched in #${data.channel_name || "channel"}!`,
      });
      loadData();
    } catch (err: any) {
      setToast({ type: "error", message: err.message || "Failed to launch giveaway" });
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6 pb-24">
        <CardSkeleton />
        <CardSkeleton />
      </div>
    );
  }

  const selectedChannel = channels.find((c) => c.id === targetChannelId);
  const requiredRole = roles.find((r) => r.id === requiredRoleId);

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
        icon={<Gift className="w-5 h-5 text-[var(--ice-silver)]" />}
        title="Giveaways"
        description="Launch automated prize giveaways with timer countdowns, role criteria, and live Discord preview simulator."
      />

      {/* Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Form: 7 cols */}
        <div className="lg:col-span-7 space-y-6">
          <form onSubmit={handleStartGiveaway}>
            <MasterCard
              label="CREATE GIVEAWAY"
              title="Launch New Giveaway"
              description="Start a giveaway with automated winner selection and role requirements."
            >
              <div className="space-y-5 pt-2">
                {/* Channel Picker */}
                <div>
                  <label className="text-[13px] font-medium text-[var(--ice-silver)] block mb-1.5">
                    Target Channel
                  </label>
                  <ChannelSelect
                    channels={channels}
                    value={targetChannelId || ""}
                    onChange={(val) => setTargetChannelId(val || null)}
                    placeholder="Choose giveaway channel..."
                    filterType="text"
                  />
                </div>

                {/* Prize */}
                <div>
                  <label className="text-[13px] font-medium text-[var(--ice-silver)] block mb-1.5">
                    Prize Title / Item
                  </label>
                  <input
                    type="text"
                    value={prize}
                    onChange={(e) => setPrize(e.target.value)}
                    placeholder="e.g. Discord Nitro, VIP Access Key, Custom Role..."
                    className="w-full h-11 px-3.5 glass-soft border border-[var(--glass-border)] rounded-xl text-sm text-[var(--ice-silver)] focus:outline-none focus:border-[var(--ice-silver)]/50 transition-colors"
                    required
                  />
                </div>

                {/* Winners & Duration */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="text-[13px] font-medium text-[var(--ice-silver)] block mb-1.5">
                      Number of Winners
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={50}
                      value={winners}
                      onChange={(e) => setWinners(parseInt(e.target.value) || 1)}
                      className="w-full h-11 px-3.5 glass-soft border border-[var(--glass-border)] rounded-xl text-xs font-mono text-[var(--ice-silver)] focus:outline-none focus:border-[var(--ice-silver)]/50 transition-colors"
                    />
                  </div>

                  <div>
                    <label className="text-[13px] font-medium text-[var(--ice-silver)] block mb-1.5">
                      Duration
                    </label>
                    <select
                      value={durationMinutes}
                      onChange={(e) => setDurationMinutes(parseInt(e.target.value))}
                      className="w-full h-11 px-3.5 glass-soft border border-[var(--glass-border)] rounded-xl text-xs font-mono text-[var(--ice-silver)] focus:outline-none focus:border-[var(--ice-silver)]/50 transition-colors cursor-pointer"
                    >
                      <option value={10} className="bg-[#0B0709] text-[var(--ice-silver)]">10 Minutes</option>
                      <option value={30} className="bg-[#0B0709] text-[var(--ice-silver)]">30 Minutes</option>
                      <option value={60} className="bg-[#0B0709] text-[var(--ice-silver)]">1 Hour</option>
                      <option value={360} className="bg-[#0B0709] text-[var(--ice-silver)]">6 Hours</option>
                      <option value={720} className="bg-[#0B0709] text-[var(--ice-silver)]">12 Hours</option>
                      <option value={1440} className="bg-[#0B0709] text-[var(--ice-silver)]">24 Hours (1 Day)</option>
                      <option value={4320} className="bg-[#0B0709] text-[var(--ice-silver)]">3 Days</option>
                      <option value={10080} className="bg-[#0B0709] text-[var(--ice-silver)]">1 Week</option>
                    </select>
                  </div>
                </div>

                {/* Role Requirement */}
                <div>
                  <label className="text-[13px] font-medium text-[var(--ice-silver)] block mb-1.5">
                    Required Role Requirement (Optional)
                  </label>
                  <RoleSelect
                    roles={roles}
                    value={requiredRoleId || ""}
                    onChange={(val) => setRequiredRoleId(val || null)}
                    placeholder="None (Open to all members)..."
                  />
                  <p className="text-[11px] text-[var(--text-muted)] mt-1.5">
                    If selected, only members holding this role will be eligible to enter.
                  </p>
                </div>

                {/* Submit Button */}
                <div className="pt-3 border-t border-[var(--glass-border)]">
                  <button
                    type="submit"
                    disabled={submitting}
                    className="w-full sm:w-auto px-6 py-2.5 bg-[var(--ice-silver)] text-[var(--ink)] font-mono text-xs font-bold uppercase tracking-wider rounded-xl shadow-md hover:opacity-90 transition-all disabled:opacity-40 flex items-center justify-center gap-2 cursor-pointer"
                  >
                    <Gift className="w-4 h-4" />
                    <span>{submitting ? "Deploying..." : "Launch Giveaway"}</span>
                  </button>
                </div>
              </div>
            </MasterCard>
          </form>
        </div>

        {/* Right: Live Preview (5 cols) */}
        <div className="lg:col-span-5 lg:sticky lg:top-24 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono tracking-[0.2em] uppercase text-[var(--hint)] font-bold">
              DISCORD LIVE PREVIEW
            </span>
            <span className="text-[11px] font-mono text-[var(--text-muted)]">
              #{selectedChannel?.name || "giveaways"}
            </span>
          </div>

          <div className="bg-[#313338] border border-[#2b2d31] rounded-2xl overflow-hidden shadow-2xl">
            <div className="bg-[#2b2d31] px-4 py-2.5 border-b border-[#1f2023] flex items-center justify-between text-xs text-[#dbdee1] font-semibold select-none">
              <span>#{selectedChannel?.name || "giveaways"}</span>
              <span className="text-[10px] font-mono text-[#949ba4] tracking-wider uppercase">
                Simulated
              </span>
            </div>

            <div className="p-4 space-y-3">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-full bg-[#5865F2] flex items-center justify-center text-white font-bold text-sm shrink-0">
                  N
                </div>
                <div className="space-y-1.5 flex-1 min-w-0">
                  <div className="flex items-baseline gap-2">
                    <span className="font-semibold text-sm text-white">Nexus</span>
                    <span className="bg-[#5865F2] text-white text-[10px] font-bold px-1.5 py-0.5 rounded uppercase leading-none">
                      APP
                    </span>
                    <span className="text-xs text-[#949ba4]">Today at 4:20 PM</span>
                  </div>

                  <div
                    className="bg-[#2b2d31] rounded-lg p-3.5 border-l-[4px] space-y-2.5 shadow-md"
                    style={{ borderLeftColor: "#DDE3E8" }}
                  >
                    <div className="flex items-center gap-2 text-white font-bold text-sm">
                      <Gift className="w-4 h-4 text-[var(--ice-silver)]" />
                      <span>{prize || "Giveaway Prize"}</span>
                    </div>

                    <div className="text-xs text-[#dbdee1] space-y-1">
                      <div>React with the entry button below to enter!</div>
                      <div>Winners: <strong>{winners}</strong></div>
                      {requiredRole && <div>Required Role: <strong>@{requiredRole.name}</strong></div>}
                      <div>Ends in: <strong>{durationMinutes} minutes</strong></div>
                    </div>

                    <div className="pt-2 border-t border-white/5 flex items-center gap-2">
                      <span className="px-3 py-1 bg-[#4e5058] rounded text-xs font-semibold text-white flex items-center gap-1.5">
                        <Gift className="w-3.5 h-3.5" />
                        <span>Enter (0)</span>
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Active Giveaways Table */}
      <MasterCard
        label="LIVE CAMPAIGNS"
        title={`Active Giveaways (${giveaways.length})`}
        description="Ongoing giveaways currently running in server channels."
      >
        {giveaways.length === 0 ? (
          <EmptyState
            icon={<Gift className="w-8 h-8 text-[var(--hint)]" />}
            title="No Active Giveaways"
            description="Launch a giveaway using the panel above."
          />
        ) : (
          <div className="space-y-3 pt-2">
            {giveaways.map((g) => (
              <div
                key={g.id || g.message_id}
                className="p-4 glass-soft border border-[var(--glass-border)] rounded-xl flex items-center justify-between gap-4"
              >
                <div>
                  <div className="font-bold text-sm text-[var(--ice-silver)]">{g.prize}</div>
                  <div className="text-xs text-[var(--text-muted)] font-mono mt-0.5">
                    {g.winners} winner(s) • Channel: #{g.channel_name || g.channel_id}
                  </div>
                </div>
                <span className="px-2.5 py-1 rounded-full glass border border-[var(--success)]/30 text-[var(--success)] text-[10px] font-mono uppercase font-bold">
                  Active
                </span>
              </div>
            ))}
          </div>
        )}
      </MasterCard>
    </div>
  );
}

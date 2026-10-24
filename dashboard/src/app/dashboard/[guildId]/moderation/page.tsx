"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ChannelSelect, Channel } from "@/components/ChannelSelect";
import { Toast } from "@/components/Toast";
import { CardSkeleton } from "@/components/Skeleton";
import { PageHeader } from "@/components/ui/PageHeader";
import { MasterCard } from "@/components/ui/MasterCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import {
  Gavel,
  ShieldAlert,
  AlertTriangle,
  Clock,
  Lock,
  Unlock,
  Sparkles,
  User,
  History,
  CheckCircle2,
} from "lucide-react";

interface Member {
  id: string;
  name: string;
  displayName: string;
  avatar: string | null;
}

export default function ModerationPage() {
  const params = useParams();
  const guildId = params.guildId as string;

  const [cases, setCases] = useState<any[]>([]);
  const [warnings, setWarnings] = useState<any[]>([]);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [guildInfo, setGuildInfo] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [activeTab, setActiveTab] = useState<"dispatcher" | "records">("dispatcher");
  const [toast, setToast] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Mod action form state
  const [action, setAction] = useState<"warn" | "mute" | "kick" | "ban" | "lock" | "unlock">("warn");
  const [targetMemberId, setTargetMemberId] = useState("");
  const [targetChannelId, setTargetChannelId] = useState("");
  const [reason, setReason] = useState("Rule violation (inappropriate content/spam)");
  const [durationMinutes, setDurationMinutes] = useState(60);

  const loadData = async () => {
    try {
      setLoading(true);
      const [casesRes, warnsRes, chRes, memRes, gRes] = await Promise.all([
        fetch(`/api/backend/guilds/${guildId}/modlog?page=1&limit=15`),
        fetch(`/api/backend/guilds/${guildId}/warnings`),
        fetch(`/api/backend/guilds/${guildId}/channels`),
        fetch(`/api/backend/guilds/${guildId}/members?limit=80`),
        fetch(`/api/backend/guilds/${guildId}`),
      ]);

      if (casesRes.ok) setCases(await casesRes.json());
      if (warnsRes.ok) setWarnings(await warnsRes.json());
      if (chRes.ok) {
        const chData: Channel[] = await chRes.json();
        setChannels(chData);
        const firstText = chData.find((c) => c.type === "text");
        if (firstText) setTargetChannelId(firstText.id);
      }
      if (memRes.ok) {
        const memData: Member[] = await memRes.json();
        setMembers(memData.filter((m) => !(m as any).bot));
        if (memData.length > 0) setTargetMemberId(memData[0].id);
      }
      if (gRes.ok) setGuildInfo(await gRes.json());
    } catch {
      setToast({ type: "error", message: "Failed to load moderation records" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [guildId]);

  const selectedMember = members.find((m) => m.id === targetMemberId);
  const selectedChannel = channels.find((c) => c.id === targetChannelId);

  const handleExecuteModAction = async (e: React.FormEvent) => {
    e.preventDefault();

    const targetId = action === "lock" || action === "unlock" ? targetChannelId : targetMemberId;
    if (!targetId) {
      setToast({ type: "error", message: "Please specify a target member or channel" });
      return;
    }

    try {
      setSubmitting(true);
      const res = await fetch(`/api/backend/guilds/${guildId}/moderation/action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action,
          target_id: targetId,
          reason: reason.trim(),
          duration_minutes: action === "mute" ? durationMinutes : undefined,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || data.error || "Failed to execute moderation action");
      }

      setToast({
        type: "success",
        message: data.message || "Moderation action executed successfully!",
      });
      loadData();
    } catch (err: any) {
      setToast({ type: "error", message: err.message || "Action failed" });
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

  const getActionColor = () => {
    if (action === "ban" || action === "kick") return "#F87171";
    if (action === "mute" || action === "warn") return "#FBBF24";
    if (action === "lock") return "#8E6B9A";
    return "#34D399";
  };

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
        icon={<Gavel className="w-5 h-5 text-[var(--ice-silver)]" />}
        title="Moderation"
        description="Execute actions (/warn, /mute, /kick, /ban, /lock) with real-time Discord mod case live preview."
      />

      {/* Tabs */}
      <div className="w-fit">
        <SegmentedControl
          options={[
            { label: "Actions", value: "dispatcher" },
            { label: `Infractions & Cases (${warnings.length + cases.length})`, value: "records" },
          ]}
          value={activeTab}
          onChange={(val) => setActiveTab(val as any)}
        />
      </div>

      {activeTab === "dispatcher" ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Form: 7 cols */}
          <div className="lg:col-span-7 space-y-6">
            <form onSubmit={handleExecuteModAction}>
              <MasterCard
                label="MODERATION ACTION"
                title="Execute Action"
                description="Select action category, target user ID, and reason."
              >
                <div className="space-y-5 pt-2">
                  {/* Action Selection */}
                  <div>
                    <label className="text-[13px] font-medium text-[var(--ice-silver)] block mb-2">
                      Action Type
                    </label>
                    <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
                      {[
                        { id: "warn", label: "Warn", icon: AlertTriangle },
                        { id: "mute", label: "Timeout", icon: Clock },
                        { id: "kick", label: "Kick", icon: Gavel },
                        { id: "ban", label: "Ban", icon: ShieldAlert },
                        { id: "lock", label: "Lock", icon: Lock },
                        { id: "unlock", label: "Unlock", icon: Unlock },
                      ].map((item) => {
                        const Icon = item.icon;
                        const isSelected = action === item.id;
                        return (
                          <button
                            key={item.id}
                            type="button"
                            onClick={() => setAction(item.id as any)}
                            className={`p-2.5 rounded-xl border flex flex-col items-center gap-1.5 transition-all cursor-pointer ${
                              isSelected
                                ? "bg-[var(--ice-silver)] text-[var(--ink)] border-[var(--ice-silver)] font-bold shadow-md"
                                : "glass-soft border-[var(--glass-border)] text-[var(--text-muted)] hover:text-[var(--ice-silver)]"
                            }`}
                          >
                            <Icon className="w-4 h-4" />
                            <span className="text-[11px] font-mono uppercase tracking-wider">{item.label}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Target Selector */}
                  {action === "lock" || action === "unlock" ? (
                    <div>
                      <label className="text-[13px] font-medium text-[var(--ice-silver)] block mb-1.5">
                        Target Text Channel
                      </label>
                      <ChannelSelect
                        channels={channels}
                        value={targetChannelId}
                        onChange={(val) => setTargetChannelId(val || "")}
                        filterType="text"
                        placeholder="Select channel to lock/unlock..."
                      />
                    </div>
                  ) : (
                    <div>
                      <label className="text-[13px] font-medium text-[var(--ice-silver)] block mb-1.5">
                        Target Server Member
                      </label>
                      <select
                        value={targetMemberId}
                        onChange={(e) => setTargetMemberId(e.target.value)}
                        className="w-full h-11 px-3.5 glass-soft border border-[var(--glass-border)] rounded-xl text-xs font-mono text-[var(--ice-silver)] focus:outline-none focus:border-[var(--ice-silver)]/50 transition-colors cursor-pointer"
                      >
                        {members.map((m) => (
                          <option key={m.id} value={m.id} className="bg-[#0B0709] text-[var(--ice-silver)]">
                            {m.displayName} (@{m.name}) — ID: {m.id}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}

                  {/* Timeout Duration */}
                  {action === "mute" && (
                    <div>
                      <label className="text-[13px] font-medium text-[var(--ice-silver)] block mb-1.5">
                        Timeout Duration
                      </label>
                      <select
                        value={durationMinutes}
                        onChange={(e) => setDurationMinutes(parseInt(e.target.value, 10))}
                        className="w-full h-11 px-3.5 glass-soft border border-[var(--glass-border)] rounded-xl text-xs font-mono text-[var(--ice-silver)] focus:outline-none focus:border-[var(--ice-silver)]/50 transition-colors cursor-pointer"
                      >
                        <option value={10} className="bg-[#0B0709] text-[var(--ice-silver)]">10 Minutes</option>
                        <option value={30} className="bg-[#0B0709] text-[var(--ice-silver)]">30 Minutes</option>
                        <option value={60} className="bg-[#0B0709] text-[var(--ice-silver)]">1 Hour</option>
                        <option value={180} className="bg-[#0B0709] text-[var(--ice-silver)]">3 Hours</option>
                        <option value={720} className="bg-[#0B0709] text-[var(--ice-silver)]">12 Hours</option>
                        <option value={1440} className="bg-[#0B0709] text-[var(--ice-silver)]">24 Hours (1 Day)</option>
                        <option value={4320} className="bg-[#0B0709] text-[var(--ice-silver)]">3 Days</option>
                        <option value={10080} className="bg-[#0B0709] text-[var(--ice-silver)]">1 Week</option>
                      </select>
                    </div>
                  )}

                  {/* Mandatory Reason */}
                  <div>
                    <label className="text-[13px] font-medium text-[var(--ice-silver)] block mb-1.5">
                      Mandatory Reason / Notes
                    </label>
                    <input
                      type="text"
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                      placeholder="Reason recorded in audit logs and sent to the member..."
                      className="w-full h-11 px-3.5 glass-soft border border-[var(--glass-border)] rounded-xl text-xs font-mono text-[var(--ice-silver)] focus:outline-none focus:border-[var(--ice-silver)]/50 transition-colors"
                      required
                    />
                  </div>

                  {/* Dispatch Button */}
                  <div className="pt-2 border-t border-[var(--glass-border)]">
                    <button
                      type="submit"
                      disabled={submitting}
                      className="w-full sm:w-auto px-6 py-2.5 bg-[var(--ice-silver)] text-[var(--ink)] font-mono text-xs font-bold uppercase tracking-wider rounded-xl shadow-md hover:opacity-90 transition-all disabled:opacity-40 flex items-center justify-center gap-2 cursor-pointer"
                    >
                      <Gavel className="w-3.5 h-3.5" />
                      <span>{submitting ? "Executing..." : `Execute /${action}`}</span>
                    </button>
                  </div>
                </div>
              </MasterCard>
            </form>
          </div>

          {/* Right Column: Live Mod Simulator (5 cols) */}
          <div className="lg:col-span-5 lg:sticky lg:top-24 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono tracking-[0.2em] uppercase text-[var(--hint)] font-bold">
                MOD AUDIT CASE LIVE PREVIEW
              </span>
              <span className="text-[11px] font-mono text-[var(--text-muted)]">
                #mod-logs
              </span>
            </div>

            <div className="bg-[#1e1f22] border border-[#2b2d31] rounded-2xl overflow-hidden shadow-2xl">
              <div className="bg-[#1f2023] px-4 py-2.5 border-b border-[#2b2d31] flex items-center justify-between text-xs text-gray-300 font-semibold select-none">
                <span>#mod-logs</span>
                <span className="text-[var(--warning)] flex items-center gap-1.5 text-[11px] font-mono">
                  <span className="w-1.5 h-1.5 rounded-full bg-[var(--warning)] animate-pulse" />
                  Live Preview
                </span>
              </div>

              <div className="bg-[#313338] p-4 space-y-3">
                <div className="flex items-baseline gap-2">
                  <span className="font-semibold text-sm text-white">Nexus</span>
                  <span className="bg-[#5865F2] text-white text-[10px] font-bold px-1.5 py-0.5 rounded uppercase leading-none">
                    APP
                  </span>
                  <span className="text-xs text-gray-400">Today at 4:20 PM</span>
                </div>

                {/* Mod case embed */}
                <div
                  className="bg-[#2b2d31] rounded-lg p-4 border-l-[4px] space-y-2 shadow-md"
                  style={{ borderLeftColor: getActionColor() }}
                >
                  <h4 className="font-bold text-sm text-white uppercase tracking-wider flex items-center gap-1.5">
                    <Gavel className="w-4 h-4 text-[var(--ice-silver)]" />
                    <span>Case #{cases.length + 1} • {action.toUpperCase()}</span>
                  </h4>

                  <div className="text-xs text-gray-300 space-y-1">
                    {action === "lock" || action === "unlock" ? (
                      <div><strong>Channel:</strong> #{selectedChannel?.name || "channel"}</div>
                    ) : (
                      <div>
                        <strong>Target:</strong> @{selectedMember?.displayName || selectedMember?.name || "Member"} (ID: {targetMemberId || "..."})
                      </div>
                    )}
                    <div><strong>Moderator:</strong> Staff Team</div>
                    {action === "mute" && (
                      <div><strong>Duration:</strong> {durationMinutes} minute(s)</div>
                    )}
                    <div><strong>Reason:</strong> {reason || "Rule violation"}</div>
                  </div>

                  <div className="text-[11px] text-gray-400 pt-2 border-t border-white/5 font-mono">
                    Nexus Moderation • {guildInfo?.name || "Server"}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* Infractions & Cases Tab */
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="glass rounded-2xl p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[var(--glass-border)]">
              <div>
                <div className="text-[10px] font-mono tracking-[0.2em] uppercase text-[var(--hint)]">
                  WARNINGS
                </div>
                <h3 className="font-display font-bold text-base text-[var(--ice-silver)]">
                  Warning Records ({warnings.length})
                </h3>
              </div>
              <AlertTriangle className="w-5 h-5 text-[var(--warning)]" />
            </div>

            {warnings.length === 0 ? (
              <div className="text-center py-8 text-[var(--text-muted)] text-xs">
                No active warnings logged for this server.
              </div>
            ) : (
              <div className="space-y-2.5">
                {warnings.slice(0, 10).map((w) => (
                  <div
                    key={w.id}
                    className="p-3.5 glass-soft border border-[var(--glass-border)] rounded-xl text-xs flex items-center justify-between gap-3"
                  >
                    <div>
                      <div className="font-bold text-[var(--ice-silver)] font-mono">Case #{w.id}</div>
                      <div className="text-[var(--text-muted)] font-mono text-[11px]">User ID: {w.user_id}</div>
                      <div className="text-[var(--text-muted)] text-[11px] mt-0.5">"{w.reason}"</div>
                    </div>
                    <span className="px-2 py-0.5 rounded-full glass border border-[var(--warning)]/30 text-[var(--warning)] text-[10px] font-mono uppercase font-bold shrink-0">
                      Warning
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="glass rounded-2xl p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[var(--glass-border)]">
              <div>
                <div className="text-[10px] font-mono tracking-[0.2em] uppercase text-[var(--hint)]">
                  CASE HISTORY
                </div>
                <h3 className="font-display font-bold text-base text-[var(--ice-silver)]">
                  Recent Mod Cases ({cases.length})
                </h3>
              </div>
              <ShieldAlert className="w-5 h-5 text-[var(--ice-silver)]" />
            </div>

            {cases.length === 0 ? (
              <div className="text-center py-8 text-[var(--text-muted)] text-xs">
                No moderation cases recorded in database yet.
              </div>
            ) : (
              <div className="space-y-2.5">
                {cases.slice(0, 10).map((c) => (
                  <div
                    key={c.case_id || c.id}
                    className="p-3.5 glass-soft border border-[var(--glass-border)] rounded-xl text-xs flex items-center justify-between gap-3"
                  >
                    <div>
                      <div className="font-bold text-[var(--ice-silver)] font-mono">Case #{c.case_id || c.id}</div>
                      <div className="text-[var(--text-muted)] font-mono text-[11px]">Action: <span className="uppercase text-[var(--ice-silver)]">{c.action}</span></div>
                      <div className="text-[var(--text-muted)] text-[11px] mt-0.5">"{c.reason}"</div>
                    </div>
                    <span className="px-2 py-0.5 rounded-full glass border border-[var(--glass-border)] text-[var(--ice-silver)] text-[10px] font-mono uppercase font-bold shrink-0">
                      {c.action}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

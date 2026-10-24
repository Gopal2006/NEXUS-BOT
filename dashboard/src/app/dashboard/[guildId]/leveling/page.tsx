"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ChannelSelect, Channel } from "@/components/ChannelSelect";
import { RoleSelect, Role } from "@/components/RoleSelect";
import { Toast } from "@/components/Toast";
import { CardSkeleton } from "@/components/Skeleton";
import { PageHeader } from "@/components/ui/PageHeader";
import { MasterCard } from "@/components/ui/MasterCard";
import { FeatureRow } from "@/components/ui/FeatureRow";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { StickySaveBar } from "@/components/ui/StickySaveBar";
import { CountUp } from "@/components/ui/CountUp";
import { Trophy, Award, Sliders, MessageSquare, Plus, Trash2, Medal, Users } from "lucide-react";

export default function LevelingPage() {
  const params = useParams();
  const guildId = params.guildId as string;

  const [leveling, setLeveling] = useState<any>({});
  const [initialLeveling, setInitialLeveling] = useState<any>({});
  const [leaderboard, setLeaderboard] = useState<any[]>([]);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState<"config" | "leaderboard">("config");
  const [toast, setToast] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Role reward addition state
  const [newRewardLevel, setNewRewardLevel] = useState<string>("5");
  const [newRewardRoleId, setNewRewardRoleId] = useState<string>("");

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const [lvlRes, lbRes, chRes, rRes] = await Promise.all([
          fetch(`/api/backend/guilds/${guildId}/leveling`),
          fetch(`/api/backend/guilds/${guildId}/leveling/leaderboard?page=1&limit=10`),
          fetch(`/api/backend/guilds/${guildId}/channels`),
          fetch(`/api/backend/guilds/${guildId}/roles`),
        ]);

        if (lvlRes.ok) {
          const data = await lvlRes.json();
          setLeveling(data);
          setInitialLeveling(data);
        }
        if (lbRes.ok) setLeaderboard(await lbRes.json());
        if (chRes.ok) setChannels(await chRes.json());
        if (rRes.ok) setRoles(await rRes.json());
      } catch {
        setToast({ type: "error", message: "Failed to load leveling system settings" });
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [guildId]);

  const hasChanges = JSON.stringify(leveling) !== JSON.stringify(initialLeveling);

  const handleSave = async () => {
    try {
      setSaving(true);
      const res = await fetch(`/api/backend/guilds/${guildId}/leveling`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(leveling),
      });

      if (!res.ok) throw new Error("Failed to save leveling settings");

      const data = await res.json();
      setLeveling(data.settings);
      setInitialLeveling(data.settings);
      setToast({ type: "success", message: "Leveling settings saved successfully!" });
    } catch (err: any) {
      setToast({ type: "error", message: err.message || "Save failed" });
    } finally {
      setSaving(false);
    }
  };

  const handleAddReward = () => {
    if (!newRewardLevel || !newRewardRoleId) return;
    const rewards = { ...(leveling.role_rewards || {}) };
    rewards[newRewardLevel] = newRewardRoleId;
    setLeveling({ ...leveling, role_rewards: rewards });
    setNewRewardRoleId("");
  };

  const handleRemoveReward = (lvl: string) => {
    const rewards = { ...(leveling.role_rewards || {}) };
    delete rewards[lvl];
    setLeveling({ ...leveling, role_rewards: rewards });
  };

  if (loading) {
    return (
      <div className="space-y-6 pb-24">
        <CardSkeleton />
        <CardSkeleton />
      </div>
    );
  }

  const isEnabled = !!leveling.enabled;

  return (
    <div className="space-y-8 animate-in fade-in duration-200 pb-28 font-sans">
      {toast && (
        <Toast
          type={toast.type}
          message={toast.message}
          onClose={() => setToast(null)}
        />
      )}

      {/* Page Header */}
      <PageHeader
        icon={<Trophy className="w-5 h-5 text-[var(--ice-silver)]" />}
        title="Leveling & Activity XP"
        description="Reward active chatters with dynamic experience points, level announcements, and milestone roles."
      />

      {/* Tabs */}
      <div className="w-fit">
        <SegmentedControl
          options={[
            { label: "Configuration", value: "config" },
            { label: `Leaderboard (${leaderboard.length})`, value: "leaderboard" },
          ]}
          value={activeTab}
          onChange={(val) => setActiveTab(val as any)}
        />
      </div>

      {activeTab === "config" ? (
        <div className="space-y-6">
          {/* Master Card for XP System */}
          <MasterCard
            label="LEVELING SYSTEM"
            title="Experience Engine"
            description="When enabled, messages generate XP on a per-minute cooldown with automatic tier calculations."
            enabled={isEnabled}
            onToggle={(val) => setLeveling({ ...leveling, enabled: val ? 1 : 0 })}
            badge={
              isEnabled ? (
                <StatusBadge status="active" label="Engine Active" />
              ) : (
                <StatusBadge status="off" label="Engine Paused" />
              )
            }
          >
            <div className="space-y-4">
              {/* Feature Row 1: Rates & Cooldown */}
              <FeatureRow
                icon={<Sliders className="w-5 h-5" />}
                title="XP Rates & Cooldown"
                description="Configure the randomized range of XP awarded per message and rate-limit intervals."
              >
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
                  <div>
                    <label className="text-[12px] font-medium text-[var(--ice-silver)] block mb-1">
                      Min XP per Message
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={100}
                      value={leveling.min_xp || 15}
                      onChange={(e) => setLeveling({ ...leveling, min_xp: parseInt(e.target.value) || 1 })}
                      className="w-full h-11 px-3.5 glass-soft border border-[var(--glass-border)] rounded-xl text-xs font-mono text-[var(--ice-silver)] focus:outline-none focus:border-[var(--ice-silver)]/50 transition-colors"
                    />
                  </div>

                  <div>
                    <label className="text-[12px] font-medium text-[var(--ice-silver)] block mb-1">
                      Max XP per Message
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={500}
                      value={leveling.max_xp || 25}
                      onChange={(e) => setLeveling({ ...leveling, max_xp: parseInt(e.target.value) || 1 })}
                      className="w-full h-11 px-3.5 glass-soft border border-[var(--glass-border)] rounded-xl text-xs font-mono text-[var(--ice-silver)] focus:outline-none focus:border-[var(--ice-silver)]/50 transition-colors"
                    />
                  </div>

                  <div>
                    <label className="text-[12px] font-medium text-[var(--ice-silver)] block mb-1">
                      Cooldown (Seconds)
                    </label>
                    <input
                      type="number"
                      min={5}
                      max={3600}
                      value={leveling.cooldown_seconds || 60}
                      onChange={(e) => setLeveling({ ...leveling, cooldown_seconds: parseInt(e.target.value) || 5 })}
                      className="w-full h-11 px-3.5 glass-soft border border-[var(--glass-border)] rounded-xl text-xs font-mono text-[var(--ice-silver)] focus:outline-none focus:border-[var(--ice-silver)]/50 transition-colors"
                    />
                  </div>
                </div>
              </FeatureRow>

              {/* Feature Row 2: Level-Up Announcement */}
              <FeatureRow
                icon={<MessageSquare className="w-5 h-5" />}
                title="Level-Up Milestone Announcement"
                description="Choose the destination channel and message template delivered upon leveling up."
              >
                <div className="space-y-4 pt-2">
                  <div>
                    <label className="text-[12px] font-medium text-[var(--ice-silver)] block mb-1">
                      Announcement Channel (Leave empty to announce in current chat)
                    </label>
                    <ChannelSelect
                      channels={channels}
                      value={leveling.channel_id ? String(leveling.channel_id) : ""}
                      onChange={(val) => setLeveling({ ...leveling, channel_id: val || null })}
                      placeholder="Announce in current active channel..."
                      filterType="text"
                    />
                  </div>

                  <div>
                    <label className="text-[12px] font-medium text-[var(--ice-silver)] block mb-1">
                      Custom Levelup Template
                    </label>
                    <input
                      type="text"
                      value={leveling.levelup_message || "GG {mention}, you reached level {level}!"}
                      onChange={(e) => setLeveling({ ...leveling, levelup_message: e.target.value })}
                      className="w-full h-11 px-3.5 glass-soft border border-[var(--glass-border)] rounded-xl text-xs font-mono text-[var(--ice-silver)] focus:outline-none focus:border-[var(--ice-silver)]/50 transition-colors"
                    />
                    <p className="text-[11px] text-[var(--text-muted)] mt-1.5 font-mono">
                      Variables: <code className="text-[var(--ice-silver)]">{`{mention}`}</code>, <code className="text-[var(--ice-silver)]">{`{name}`}</code>, <code className="text-[var(--ice-silver)]">{`{level}`}</code>, <code className="text-[var(--ice-silver)]">{`{xp}`}</code>.
                    </p>
                  </div>
                </div>
              </FeatureRow>

              {/* Feature Row 3: Role Rewards */}
              <FeatureRow
                icon={<Award className="w-5 h-5" />}
                title="Milestone Role Rewards"
                description="Automatically award roles when members reach designated level thresholds."
                badge={
                  <span className="text-xs font-mono text-[var(--text-muted)]">
                    {Object.keys(leveling.role_rewards || {}).length} configured
                  </span>
                }
              >
                <div className="space-y-4 pt-2">
                  <div className="flex flex-col sm:flex-row items-end gap-3 p-3.5 glass-soft rounded-xl border border-[var(--glass-border)]">
                    <div className="w-full sm:w-28">
                      <label className="text-[11px] font-mono uppercase tracking-wider text-[var(--text-muted)] block mb-1">Target Level</label>
                      <input
                        type="number"
                        min={1}
                        value={newRewardLevel}
                        onChange={(e) => setNewRewardLevel(e.target.value)}
                        className="w-full h-10 px-3 glass-soft border border-[var(--glass-border)] rounded-lg text-xs font-mono text-[var(--ice-silver)] focus:outline-none focus:border-[var(--ice-silver)]/50"
                      />
                    </div>
                    <div className="w-full flex-1">
                      <label className="text-[11px] font-mono uppercase tracking-wider text-[var(--text-muted)] block mb-1">Role Reward</label>
                      <RoleSelect
                        roles={roles}
                        value={newRewardRoleId}
                        onChange={(val) => setNewRewardRoleId(val || "")}
                        placeholder="Choose role to reward..."
                      />
                    </div>
                    <button
                      type="button"
                      onClick={handleAddReward}
                      className="px-4 py-2.5 bg-[var(--ice-silver)] text-[var(--ink)] rounded-xl text-xs font-mono uppercase font-bold tracking-wider hover:opacity-90 transition-all flex items-center gap-1.5 shrink-0 cursor-pointer shadow-sm"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      <span>Add Reward</span>
                    </button>
                  </div>

                  <div className="space-y-2">
                    {Object.entries(leveling.role_rewards || {}).length === 0 ? (
                      <div className="text-center py-4 text-[var(--text-muted)] text-xs">
                        No milestone roles configured yet.
                      </div>
                    ) : (
                      Object.entries(leveling.role_rewards || {}).map(([lvl, roleId]) => {
                        const role = roles.find((r) => r.id === roleId);
                        return (
                          <div
                            key={lvl}
                            className="p-3 glass-soft border border-[var(--glass-border)] rounded-xl flex items-center justify-between gap-3 text-xs"
                          >
                            <div className="flex items-center gap-3">
                              <span className="px-2 py-0.5 rounded-md glass border border-[var(--glass-border)] font-mono font-bold text-[var(--ice-silver)]">
                                Level {lvl}
                              </span>
                              <span className="font-medium text-[var(--ice-silver)]">
                                @{role?.name || `Role (${roleId})`}
                              </span>
                            </div>
                            <button
                              type="button"
                              onClick={() => handleRemoveReward(lvl)}
                              className="p-1.5 rounded-lg text-[var(--error)] hover:bg-[var(--error)]/10 transition-colors cursor-pointer"
                              title="Delete milestone reward"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              </FeatureRow>
            </div>
          </MasterCard>

          {/* Sticky Save Bar */}
          <StickySaveBar
            hasChanges={hasChanges}
            loading={saving}
            onSave={handleSave}
            onDiscard={() => setLeveling(initialLeveling)}
          />
        </div>
      ) : (
        /* Leaderboard Tab */
        <div className="glass rounded-2xl p-6 sm:p-8 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[var(--glass-border)]">
            <div>
              <div className="text-[10px] font-mono tracking-[0.2em] uppercase text-[var(--hint)]">
                LEADERBOARD
              </div>
              <h3 className="font-display font-bold text-lg text-[var(--ice-silver)]">
                Top Active Members
              </h3>
            </div>
            <Users className="w-5 h-5 text-[var(--hint)]" />
          </div>

          {leaderboard.length === 0 ? (
            <div className="text-center py-12 text-[var(--text-muted)] text-xs">
              No activity XP recorded on this server yet.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-[var(--glass-border)] text-[var(--text-faint)] uppercase tracking-wider font-mono text-[11px]">
                    <th className="py-3 px-3">Rank</th>
                    <th className="py-3 px-3">Member (User ID)</th>
                    <th className="py-3 px-3">Level</th>
                    <th className="py-3 px-3">Total XP</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--glass-border)]">
                  {leaderboard.map((user, idx) => (
                    <tr key={user.user_id || idx} className="hover:bg-[var(--glass-bg-strong)]/30 transition-colors">
                      <td className="py-3.5 px-3 font-mono font-bold text-[var(--ice-silver)]">
                        #{idx + 1}
                      </td>
                      <td className="py-3.5 px-3 font-mono text-[var(--ice-silver)]">
                        {user.name || `@${user.user_id}`}
                      </td>
                      <td className="py-3.5 px-3">
                        <span className="px-2.5 py-1 rounded-md glass-soft border border-[var(--glass-border)] text-[var(--ice-silver)] font-bold font-mono">
                          Lvl {user.level || 1}
                        </span>
                      </td>
                      <td className="py-3.5 px-3 font-mono text-[var(--text-muted)]">
                        <CountUp end={user.xp || 0} /> XP
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

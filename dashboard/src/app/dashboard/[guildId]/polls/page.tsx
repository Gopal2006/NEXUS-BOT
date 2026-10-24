"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ChannelSelect, Channel } from "@/components/ChannelSelect";
import { Toast } from "@/components/Toast";
import { CardSkeleton } from "@/components/Skeleton";
import { PageHeader } from "@/components/ui/PageHeader";
import { MasterCard } from "@/components/ui/MasterCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { BarChart3, Plus, Trash2, Send, CheckSquare, Clock } from "lucide-react";

export default function PollsPage() {
  const params = useParams();
  const guildId = params.guildId as string;

  const [polls, setPolls] = useState<any[]>([]);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [guildInfo, setGuildInfo] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [toast, setToast] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Poll form state
  const [targetChannelId, setTargetChannelId] = useState<string | null>(null);
  const [question, setQuestion] = useState("What game should we host for community night?");
  const [options, setOptions] = useState<string[]>([
    "Minecraft",
    "Among Us",
    "Valorant",
  ]);
  const [durationMinutes, setDurationMinutes] = useState(120);

  const loadData = async () => {
    try {
      setLoading(true);
      const [pollsRes, chRes, gRes] = await Promise.all([
        fetch(`/api/backend/guilds/${guildId}/polls`),
        fetch(`/api/backend/guilds/${guildId}/channels`),
        fetch(`/api/backend/guilds/${guildId}`),
      ]);

      if (pollsRes.ok) setPolls(await pollsRes.json());
      if (chRes.ok) {
        const chData: Channel[] = await chRes.json();
        setChannels(chData);
        const preferred = chData.find((c) => c.type === "text" && (c.name.includes("poll") || c.name.includes("general"))) || chData.find(c => c.type === "text");
        if (preferred) setTargetChannelId(preferred.id);
      }
      if (gRes.ok) setGuildInfo(await gRes.json());
    } catch {
      setToast({ type: "error", message: "Failed to load polls" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [guildId]);

  const addOption = () => {
    if (options.length >= 10) return;
    setOptions([...options, `Option ${options.length + 1}`]);
  };

  const removeOption = (idx: number) => {
    if (options.length <= 2) return;
    setOptions(options.filter((_, i) => i !== idx));
  };

  const updateOption = (idx: number, val: string) => {
    const updated = [...options];
    updated[idx] = val;
    setOptions(updated);
  };

  const handleCreatePoll = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetChannelId) {
      setToast({ type: "error", message: "Please select a channel for the poll" });
      return;
    }
    if (!question.trim()) {
      setToast({ type: "error", message: "Please specify a question" });
      return;
    }
    const cleanOptions = options.map(o => o.trim()).filter(Boolean);
    if (cleanOptions.length < 2) {
      setToast({ type: "error", message: "A poll requires at least 2 options" });
      return;
    }

    try {
      setSubmitting(true);
      const res = await fetch(`/api/backend/guilds/${guildId}/polls/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          channel_id: targetChannelId,
          question: question.trim(),
          options: cleanOptions,
          duration_minutes: durationMinutes,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || data.error || "Failed to create poll");
      }

      setToast({
        type: "success",
        message: `Poll successfully posted in #${data.channel_name || "channel"}!`,
      });
      loadData();
    } catch (err: any) {
      setToast({ type: "error", message: err.message || "Failed to create poll" });
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
        icon={<BarChart3 className="w-5 h-5 text-[var(--ice-silver)]" />}
        title="Community Polls"
        description="Deploy interactive decision polls with numbered vote options and automatic closing timers."
      />

      {/* Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Form: 7 cols */}
        <div className="lg:col-span-7 space-y-6">
          <form onSubmit={handleCreatePoll}>
            <MasterCard
              label="CREATE POLL"
              title="Create New Poll"
              description="Configure poll question, options, target channel, and expiration window."
            >
              <div className="space-y-5 pt-2">
                {/* Target Channel */}
                <div>
                  <label className="text-[13px] font-medium text-[var(--ice-silver)] block mb-1.5">
                    Target Channel
                  </label>
                  <ChannelSelect
                    channels={channels}
                    value={targetChannelId || ""}
                    onChange={(val) => setTargetChannelId(val || null)}
                    placeholder="Choose poll channel..."
                    filterType="text"
                  />
                </div>

                {/* Question */}
                <div>
                  <label className="text-[13px] font-medium text-[var(--ice-silver)] block mb-1.5">
                    Poll Question
                  </label>
                  <input
                    type="text"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder="What game should we host this weekend?"
                    className="w-full h-11 px-3.5 glass-soft border border-[var(--glass-border)] rounded-xl text-sm text-[var(--ice-silver)] focus:outline-none focus:border-[var(--ice-silver)]/50 transition-colors"
                    required
                  />
                </div>

                {/* Options List */}
                <div className="space-y-2.5">
                  <div className="flex items-center justify-between">
                    <label className="text-[13px] font-medium text-[var(--ice-silver)]">
                      Vote Options ({options.length}/10)
                    </label>
                    {options.length < 10 && (
                      <button
                        type="button"
                        onClick={addOption}
                        className="text-xs font-mono text-[var(--ice-silver)] hover:underline flex items-center gap-1 cursor-pointer"
                      >
                        <Plus className="w-3 h-3" />
                        <span>Add Option</span>
                      </button>
                    )}
                  </div>

                  {options.map((opt, idx) => (
                    <div key={idx} className="flex items-center gap-2">
                      <span className="w-8 h-10 rounded-lg glass-soft border border-[var(--glass-border)] flex items-center justify-center font-mono text-xs font-bold text-[var(--ice-silver)] shrink-0">
                        {idx + 1}
                      </span>
                      <input
                        type="text"
                        value={opt}
                        onChange={(e) => updateOption(idx, e.target.value)}
                        placeholder={`Option ${idx + 1}`}
                        className="flex-1 h-10 px-3 glass-soft border border-[var(--glass-border)] rounded-xl text-xs text-[var(--ice-silver)] focus:outline-none focus:border-[var(--ice-silver)]/50 transition-colors"
                        required
                      />
                      {options.length > 2 && (
                        <button
                          type="button"
                          onClick={() => removeOption(idx)}
                          className="p-2 glass-soft border border-[var(--error)]/30 text-[var(--error)] hover:bg-[var(--error)]/10 rounded-lg cursor-pointer transition-colors"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  ))}
                </div>

                {/* Duration */}
                <div>
                  <label className="text-[13px] font-medium text-[var(--ice-silver)] block mb-1.5">
                    Poll Active Window
                  </label>
                  <select
                    value={durationMinutes}
                    onChange={(e) => setDurationMinutes(parseInt(e.target.value))}
                    className="w-full h-11 px-3.5 glass-soft border border-[var(--glass-border)] rounded-xl text-xs font-mono text-[var(--ice-silver)] focus:outline-none focus:border-[var(--ice-silver)]/50 transition-colors cursor-pointer"
                  >
                    <option value={30} className="bg-[#0B0709] text-[var(--ice-silver)]">30 Minutes</option>
                    <option value={60} className="bg-[#0B0709] text-[var(--ice-silver)]">1 Hour</option>
                    <option value={120} className="bg-[#0B0709] text-[var(--ice-silver)]">2 Hours</option>
                    <option value={360} className="bg-[#0B0709] text-[var(--ice-silver)]">6 Hours</option>
                    <option value={720} className="bg-[#0B0709] text-[var(--ice-silver)]">12 Hours</option>
                    <option value={1440} className="bg-[#0B0709] text-[var(--ice-silver)]">24 Hours (1 Day)</option>
                    <option value={4320} className="bg-[#0B0709] text-[var(--ice-silver)]">3 Days</option>
                    <option value={10080} className="bg-[#0B0709] text-[var(--ice-silver)]">1 Week</option>
                  </select>
                </div>

                {/* Submit Button */}
                <div className="pt-3 border-t border-[var(--glass-border)]">
                  <button
                    type="submit"
                    disabled={submitting}
                    className="w-full sm:w-auto px-6 py-2.5 bg-[var(--ice-silver)] text-[var(--ink)] font-mono text-xs font-bold uppercase tracking-wider rounded-xl shadow-md hover:opacity-90 transition-all disabled:opacity-40 flex items-center justify-center gap-2 cursor-pointer"
                  >
                    <BarChart3 className="w-4 h-4" />
                    <span>{submitting ? "Deploying..." : "Deploy Poll"}</span>
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
              #{selectedChannel?.name || "polls"}
            </span>
          </div>

          <div className="bg-[#313338] border border-[#2b2d31] rounded-2xl overflow-hidden shadow-2xl">
            <div className="bg-[#2b2d31] px-4 py-2.5 border-b border-[#1f2023] flex items-center justify-between text-xs text-[#dbdee1] font-semibold select-none">
              <span>#{selectedChannel?.name || "polls"}</span>
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
                    <div className="font-bold text-sm text-white flex items-center gap-2">
                      <BarChart3 className="w-4 h-4 text-[var(--ice-silver)]" />
                      <span>{question || "Poll Question"}</span>
                    </div>

                    <div className="space-y-1.5 text-xs text-[#dbdee1]">
                      {options.filter(Boolean).map((opt, idx) => (
                        <div key={idx} className="flex items-center gap-2">
                          <span className="w-5 h-5 rounded bg-[#383a40] text-center leading-5 text-[11px] font-mono font-bold text-white shrink-0">
                            {idx + 1}
                          </span>
                          <span>{opt}</span>
                        </div>
                      ))}
                    </div>

                    <div className="pt-2 border-t border-white/5 text-[11px] text-[#949ba4] flex items-center justify-between font-mono">
                      <span>Expires in {durationMinutes}m</span>
                      <span>Total votes: 0</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Active Polls Table */}
      <MasterCard
        label="ACTIVE POLLS"
        title={`Active Polls (${polls.length})`}
        description="Ongoing polls currently collecting votes in server channels."
      >
        {polls.length === 0 ? (
          <EmptyState
            icon={<BarChart3 className="w-8 h-8 text-[var(--hint)]" />}
            title="No Active Polls"
            description="Create a poll using the panel above."
          />
        ) : (
          <div className="space-y-3 pt-2">
            {polls.map((p) => (
              <div
                key={p.id || p.message_id}
                className="p-4 glass-soft border border-[var(--glass-border)] rounded-xl flex items-center justify-between gap-4"
              >
                <div>
                  <div className="font-bold text-sm text-[var(--ice-silver)]">{p.question}</div>
                  <div className="text-xs text-[var(--text-muted)] font-mono mt-0.5">
                    {p.options?.length || 0} options • Channel: #{p.channel_name || p.channel_id}
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

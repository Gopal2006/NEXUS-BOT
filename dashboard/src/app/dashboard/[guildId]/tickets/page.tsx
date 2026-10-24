"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ChannelSelect, Channel } from "@/components/ChannelSelect";
import { Toast } from "@/components/Toast";
import { CardSkeleton } from "@/components/Skeleton";
import { PageHeader } from "@/components/ui/PageHeader";
import { MasterCard } from "@/components/ui/MasterCard";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { EmptyState } from "@/components/ui/EmptyState";
import { Ticket, Send, CheckCircle2, Clock, MessageSquare, Shield, ArrowRight, FileText } from "lucide-react";

export default function TicketsPage() {
  const params = useParams();
  const guildId = params.guildId as string;

  const [tickets, setTickets] = useState<any[]>([]);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [guildInfo, setGuildInfo] = useState<any>(null);
  const [settings, setSettings] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [activeTab, setActiveTab] = useState<"panel" | "records">("panel");
  const [toast, setToast] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Panel setup form state
  const [targetChannelId, setTargetChannelId] = useState<string | null>(null);
  const [panelTitle, setPanelTitle] = useState("Support Ticket Panel");
  const [panelDescription, setPanelDescription] = useState(
    "Need assistance, want to appeal a moderation case, or claim a giveaway? Click the button below to open a private ticket with our staff team."
  );
  const [buttonLabel, setButtonLabel] = useState("Open Ticket");

  const loadData = async () => {
    try {
      setLoading(true);
      const [tRes, chRes, gRes, setRes] = await Promise.all([
        fetch(`/api/backend/guilds/${guildId}/tickets`),
        fetch(`/api/backend/guilds/${guildId}/channels`),
        fetch(`/api/backend/guilds/${guildId}`),
        fetch(`/api/backend/guilds/${guildId}/settings`),
      ]);

      if (tRes.ok) setTickets(await tRes.json());
      if (chRes.ok) {
        const chData: Channel[] = await chRes.json();
        setChannels(chData);
        const preferred = chData.find(c => c.type === "text" && (c.name.includes("ticket") || c.name.includes("support") || c.name.includes("help"))) || chData.find(c => c.type === "text");
        if (preferred) setTargetChannelId(preferred.id);
      }
      if (gRes.ok) setGuildInfo(await gRes.json());
      if (setRes.ok) setSettings(await setRes.json());
    } catch {
      setToast({ type: "error", message: "Failed to load support tickets" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [guildId]);

  const handleDeployPanel = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetChannelId) {
      setToast({ type: "error", message: "Please select a channel to deploy the ticket panel" });
      return;
    }

    try {
      setSubmitting(true);
      const res = await fetch(`/api/backend/guilds/${guildId}/tickets/setup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          channel_id: targetChannelId,
          title: panelTitle.trim(),
          description: panelDescription.trim(),
          button_label: buttonLabel.trim() || "Open Ticket",
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || data.error || "Failed to deploy ticket panel");
      }

      setToast({
        type: "success",
        message: `Support ticket panel successfully published to #${data.channel_name || "channel"}!`,
      });
      loadData();
    } catch (err: any) {
      setToast({ type: "error", message: err.message || "Failed to deploy panel" });
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
  const openTickets = tickets.filter((t) => t.status === "open");
  const closedTickets = tickets.filter((t) => t.status !== "open");

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
        icon={<Ticket className="w-5 h-5 text-[var(--ice-silver)]" />}
        title="Support Tickets"
        description="Deploy interactive ticket panels with button-triggered private channel creation and transcripts."
      />

      {/* Tabs */}
      <div className="w-fit">
        <SegmentedControl
          options={[
            { label: "Deploy Panel", value: "panel" },
            { label: `Ticket Records (${openTickets.length} open)`, value: "records" },
          ]}
          value={activeTab}
          onChange={(val) => setActiveTab(val as any)}
        />
      </div>

      {activeTab === "panel" ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Form: 7 cols */}
          <div className="lg:col-span-7 space-y-6">
            <form onSubmit={handleDeployPanel}>
              <MasterCard
                label="TICKET PANEL"
                title="Deploy Support Panel"
                description="Publish an embed message with an interactive button that creates private channels for members."
              >
                <div className="space-y-5 pt-2">
                  {/* Channel Picker */}
                  <div>
                    <label className="text-[13px] font-medium text-[var(--ice-silver)] block mb-1.5">
                      Destination Channel
                    </label>
                    <ChannelSelect
                      channels={channels}
                      value={targetChannelId || ""}
                      onChange={(val) => setTargetChannelId(val || null)}
                      placeholder="Choose channel for ticket panel..."
                      filterType="text"
                    />
                  </div>

                  {/* Panel Title */}
                  <div>
                    <label className="text-[13px] font-medium text-[var(--ice-silver)] block mb-1.5">
                      Panel Title
                    </label>
                    <input
                      type="text"
                      value={panelTitle}
                      onChange={(e) => setPanelTitle(e.target.value)}
                      placeholder="Support Ticket Panel"
                      className="w-full h-11 px-3.5 glass-soft border border-[var(--glass-border)] rounded-xl text-sm text-[var(--ice-silver)] focus:outline-none focus:border-[var(--ice-silver)]/50 transition-colors"
                      required
                    />
                  </div>

                  {/* Description */}
                  <div>
                    <label className="text-[13px] font-medium text-[var(--ice-silver)] block mb-1.5">
                      Panel Instructions & Information
                    </label>
                    <textarea
                      rows={4}
                      value={panelDescription}
                      onChange={(e) => setPanelDescription(e.target.value)}
                      placeholder="Instructions for opening a ticket..."
                      className="w-full p-3.5 glass-soft border border-[var(--glass-border)] rounded-xl text-xs font-mono text-[var(--ice-silver)] focus:outline-none focus:border-[var(--ice-silver)]/50 transition-colors resize-none leading-relaxed"
                      required
                    />
                  </div>

                  {/* Button Label */}
                  <div>
                    <label className="text-[13px] font-medium text-[var(--ice-silver)] block mb-1.5">
                      Button Label
                    </label>
                    <input
                      type="text"
                      value={buttonLabel}
                      onChange={(e) => setButtonLabel(e.target.value)}
                      placeholder="Open Ticket"
                      className="w-full h-11 px-3.5 glass-soft border border-[var(--glass-border)] rounded-xl text-xs font-mono text-[var(--ice-silver)] focus:outline-none focus:border-[var(--ice-silver)]/50 transition-colors"
                    />
                  </div>

                  {/* Submit Button */}
                  <div className="pt-3 border-t border-[var(--glass-border)]">
                    <button
                      type="submit"
                      disabled={submitting}
                      className="w-full sm:w-auto px-6 py-2.5 bg-[var(--ice-silver)] text-[var(--ink)] font-mono text-xs font-bold uppercase tracking-wider rounded-xl shadow-md hover:opacity-90 transition-all disabled:opacity-40 flex items-center justify-center gap-2 cursor-pointer"
                    >
                      <Ticket className="w-4 h-4" />
                      <span>{submitting ? "Deploying..." : "Publish Ticket Panel"}</span>
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
                #{selectedChannel?.name || "tickets"}
              </span>
            </div>

            <div className="bg-[#313338] border border-[#2b2d31] rounded-2xl overflow-hidden shadow-2xl">
              <div className="bg-[#2b2d31] px-4 py-2.5 border-b border-[#1f2023] flex items-center justify-between text-xs text-[#dbdee1] font-semibold select-none">
                <span>#{selectedChannel?.name || "tickets"}</span>
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
                      style={{ borderLeftColor: "#5865F2" }}
                    >
                      <div className="font-bold text-sm text-white flex items-center gap-2">
                        <Ticket className="w-4 h-4 text-[var(--ice-silver)]" />
                        <span>{panelTitle || "Support Ticket Panel"}</span>
                      </div>

                      <div className="text-xs text-[#dbdee1] leading-relaxed whitespace-pre-wrap">
                        {panelDescription}
                      </div>

                      <div className="pt-2 border-t border-white/5">
                        <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#5865F2] text-white text-xs font-semibold rounded shadow-sm select-none">
                          <Ticket className="w-3.5 h-3.5" />
                          <span>{buttonLabel || "Open Ticket"}</span>
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* Ticket Records Tab */
        <div className="space-y-6">
          <MasterCard
            label="OPEN TICKETS"
            title={`Open Tickets (${openTickets.length})`}
            description="Currently unresolved support channels waiting on member or staff response."
          >
            {openTickets.length === 0 ? (
              <EmptyState
                icon={<Ticket className="w-8 h-8 text-[var(--hint)]" />}
                title="No Open Tickets"
                description="All member support inquiries are currently resolved."
              />
            ) : (
              <div className="space-y-2.5 pt-2">
                {openTickets.map((t) => (
                  <div
                    key={t.id}
                    className="p-4 glass-soft border border-[var(--glass-border)] rounded-xl flex items-center justify-between gap-4 text-xs"
                  >
                    <div>
                      <div className="font-bold text-[var(--ice-silver)] font-mono">
                        Ticket #{t.ticket_number || t.id}
                      </div>
                      <div className="text-[var(--text-muted)] font-mono text-[11px] mt-0.5">
                        User: {t.user_id} • Channel: {t.channel_id}
                      </div>
                    </div>
                    <span className="px-2.5 py-1 rounded-full glass border border-[var(--success)]/30 text-[var(--success)] font-mono uppercase text-[10px] font-bold">
                      Open
                    </span>
                  </div>
                ))}
              </div>
            )}
          </MasterCard>

          <MasterCard
            label="CLOSED TICKETS"
            title={`Closed Tickets (${closedTickets.length})`}
            description="Archived support inquiries with stored transcripts."
          >
            {closedTickets.length === 0 ? (
              <div className="text-center py-8 text-[var(--text-muted)] text-xs">
                No closed ticket archives.
              </div>
            ) : (
              <div className="space-y-2.5 pt-2">
                {closedTickets.slice(0, 15).map((t) => (
                  <div
                    key={t.id}
                    className="p-4 glass-soft border border-[var(--glass-border)] rounded-xl flex items-center justify-between gap-4 text-xs"
                  >
                    <div>
                      <div className="font-bold text-[var(--ice-silver)] font-mono">
                        Ticket #{t.ticket_number || t.id}
                      </div>
                      <div className="text-[var(--text-muted)] font-mono text-[11px] mt-0.5">
                        User: {t.user_id} • Status: {t.status}
                      </div>
                    </div>
                    {t.transcript_url ? (
                      <Link
                        href={t.transcript_url}
                        target="_blank"
                        className="px-3 py-1 rounded-lg glass-soft hover:bg-[var(--ice-silver)] hover:text-[var(--ink)] text-[var(--ice-silver)] font-mono text-[11px] flex items-center gap-1 transition-all"
                      >
                        <FileText className="w-3 h-3" />
                        <span>Transcript</span>
                      </Link>
                    ) : (
                      <span className="px-2.5 py-1 rounded-full glass border border-[var(--glass-border)] text-[var(--text-muted)] font-mono uppercase text-[10px]">
                        Archived
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </MasterCard>
        </div>
      )}
    </div>
  );
}

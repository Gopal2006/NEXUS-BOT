"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Toast } from "@/components/Toast";
import { CardSkeleton } from "@/components/Skeleton";
import { PageHeader } from "@/components/ui/PageHeader";
import { MasterCard } from "@/components/ui/MasterCard";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { EmptyState } from "@/components/ui/EmptyState";
import { MessageSquareText, Plus, Trash2, Zap } from "lucide-react";

export default function AutoresponderPage() {
  const params = useParams();
  const guildId = params.guildId as string;

  const [triggers, setTriggers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [toast, setToast] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Form state
  const [newTrigger, setNewTrigger] = useState("");
  const [newResponse, setNewResponse] = useState("");
  const [matchType, setMatchType] = useState<"exact" | "contains">("exact");

  const loadData = async () => {
    try {
      setLoading(true);
      const res = await fetch(`/api/backend/guilds/${guildId}/autoresponders`);
      if (res.ok) setTriggers(await res.json());
    } catch {
      setToast({ type: "error", message: "Failed to load autoresponders" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [guildId]);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTrigger.trim() || !newResponse.trim()) {
      setToast({ type: "error", message: "Please enter both trigger and response" });
      return;
    }

    try {
      setActionLoading(true);
      const res = await fetch(`/api/backend/guilds/${guildId}/autoresponders`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          trigger: newTrigger.trim(),
          response: newResponse.trim(),
          match_type: matchType,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to create autoresponder");
      }

      setToast({ type: "success", message: "Autoresponder added successfully!" });
      setNewTrigger("");
      setNewResponse("");
      await loadData();
    } catch (err: any) {
      setToast({ type: "error", message: err.message || "Failed to create" });
    } finally {
      setActionLoading(false);
    }
  };

  const handleDelete = async (trigger: string) => {
    try {
      setActionLoading(true);
      const res = await fetch(`/api/backend/guilds/${guildId}/autoresponders/${encodeURIComponent(trigger)}`, {
        method: "DELETE",
      });

      if (!res.ok) throw new Error("Failed to delete autoresponder");

      setToast({ type: "success", message: "Autoresponder deleted" });
      setTriggers((prev) => prev.filter((t) => t.trigger !== trigger));
    } catch (err: any) {
      setToast({ type: "error", message: err.message || "Failed to delete" });
    } finally {
      setActionLoading(false);
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
        icon={<MessageSquareText className="w-5 h-5 text-[var(--ice-silver)]" />}
        title="Custom Autoresponders"
        description="Configure automated bot replies triggered by specific words or phrases detected in server chat."
      />

      {/* Creation Form */}
      <form onSubmit={handleAdd}>
        <MasterCard
          label="NEW AUTORESPONDER"
          title="Create Autoresponder"
          description="Specify the trigger phrase, match method, and automated reply."
        >
          <div className="space-y-5 pt-2">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="sm:col-span-2">
                <label className="text-[13px] font-medium text-[var(--ice-silver)] block mb-1.5">
                  Trigger Keyword or Phrase
                </label>
                <input
                  type="text"
                  value={newTrigger}
                  onChange={(e) => setNewTrigger(e.target.value)}
                  placeholder="e.g. !faq or how to join"
                  className="w-full h-11 px-3.5 glass-soft border border-[var(--glass-border)] rounded-xl text-xs font-mono text-[var(--ice-silver)] focus:outline-none focus:border-[var(--ice-silver)]/50 transition-colors"
                />
              </div>

              <div>
                <label className="text-[13px] font-medium text-[var(--ice-silver)] block mb-1.5">
                  Match Mode
                </label>
                <SegmentedControl
                  options={[
                    { label: "Exact", value: "exact" },
                    { label: "Contains", value: "contains" },
                  ]}
                  value={matchType}
                  onChange={(val) => setMatchType(val as any)}
                />
              </div>
            </div>

            <div>
              <label className="text-[13px] font-medium text-[var(--ice-silver)] block mb-1.5">
                Automated Reply Text
              </label>
              <textarea
                rows={3}
                value={newResponse}
                onChange={(e) => setNewResponse(e.target.value)}
                placeholder="The message NEXUS will send in response..."
                className="w-full p-3.5 glass-soft border border-[var(--glass-border)] rounded-xl text-xs font-mono text-[var(--ice-silver)] focus:outline-none focus:border-[var(--ice-silver)]/50 transition-colors resize-none leading-relaxed"
              />
            </div>

            <div className="pt-2 border-t border-[var(--glass-border)] flex justify-end">
              <button
                type="submit"
                disabled={actionLoading || !newTrigger.trim() || !newResponse.trim()}
                className="px-5 py-2.5 rounded-xl bg-[var(--ice-silver)] text-[var(--ink)] font-mono text-xs font-bold uppercase tracking-wider hover:opacity-90 transition-all flex items-center gap-1.5 disabled:opacity-40 cursor-pointer shadow-md"
              >
                <Plus className="w-4 h-4" />
                <span>{actionLoading ? "Saving..." : "Add Autoresponder"}</span>
              </button>
            </div>
          </div>
        </MasterCard>
      </form>

      {/* Active Triggers */}
      <MasterCard
        label="ACTIVE RULES"
        title={`Active Triggers (${triggers.length})`}
        description="List of all active autoresponders on this server."
      >
        {triggers.length === 0 ? (
          <EmptyState
            icon={<MessageSquareText className="w-8 h-8 text-[var(--hint)]" />}
            title="No Autoresponders Configured"
            description="Create your first autoresponder above to automate common server answers."
          />
        ) : (
          <div className="space-y-3 pt-2">
            {triggers.map((t) => (
              <div
                key={t.trigger}
                className="p-4 glass-soft border border-[var(--glass-border)] rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4 transition-all hover:border-[var(--ice-silver)]/25"
              >
                <div className="space-y-1.5 min-w-0">
                  <div className="flex items-center gap-2.5">
                    <span className="font-mono font-bold text-xs text-[var(--ice-silver)] bg-[var(--bg-deep)] px-2.5 py-1 rounded-md border border-[var(--glass-border)]">
                      {t.trigger}
                    </span>
                    <span className="px-2 py-0.5 rounded-full glass border border-[var(--glass-border)] text-[10px] font-mono uppercase text-[var(--text-muted)]">
                      {t.match_type || "exact"}
                    </span>
                  </div>
                  <div className="text-xs text-[var(--text-muted)] leading-relaxed font-mono line-clamp-2">
                    "{t.response}"
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => handleDelete(t.trigger)}
                  disabled={actionLoading}
                  className="p-2.5 rounded-xl glass-soft border border-[var(--error)]/30 text-[var(--error)] hover:bg-[var(--error)]/10 transition-colors shrink-0 cursor-pointer self-end sm:self-auto"
                  title="Delete autoresponder"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </MasterCard>
    </div>
  );
}

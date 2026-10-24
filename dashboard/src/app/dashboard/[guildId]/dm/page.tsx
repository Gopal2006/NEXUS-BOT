"use client";

import React, { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { Send, User, Users, ShieldAlert, Sparkles } from "lucide-react";
import { RoleSelect, Role } from "@/components/RoleSelect";
import { DiscordPreview } from "@/components/DiscordPreview";
import { Toast } from "@/components/Toast";
import { PageHeader } from "@/components/ui/PageHeader";
import { Section } from "@/components/ui/Section";
import { FieldRow } from "@/components/ui/FieldRow";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { ColorSwatch } from "@/components/ui/ColorSwatch";
import { Accordion } from "@/components/ui/Accordion";
import { StickySaveBar } from "@/components/ui/StickySaveBar";

interface Member {
  id: string;
  name: string;
  displayName: string;
  bot: boolean;
  avatar: string | null;
  roles: string[];
}

export default function DirectMessagesPage() {
  const params = useParams();
  const guildId = params.guildId as string;

  const [roles, setRoles] = useState<Role[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [guildInfo, setGuildInfo] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [dispatching, setDispatching] = useState(false);
  const [toast, setToast] = useState<{ type: "success" | "error" | "warning"; message: string } | null>(null);

  // Form State
  const [targetType, setTargetType] = useState<"user" | "role">("user");
  const [targetUserId, setTargetUserId] = useState<string>("");
  const [manualUserId, setManualUserId] = useState<string>("");
  const [showCustomId, setShowCustomId] = useState(false);
  const [targetRoleId, setTargetRoleId] = useState<string | null>(null);
  const [title, setTitle] = useState("Notice from Server Administration");
  const [content, setContent] = useState(
    "Hello!\n\nThis is an important update directly from the staff team. Please review our community guidelines or claim your assigned perks."
  );
  const [color, setColor] = useState("#DDE3E8");
  const [bannerUrl, setBannerUrl] = useState("");
  const [buttonLabel, setButtonLabel] = useState("");
  const [buttonUrl, setButtonUrl] = useState("");

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const [roRes, memRes, gRes] = await Promise.all([
          fetch(`/api/backend/guilds/${guildId}/roles`),
          fetch(`/api/backend/guilds/${guildId}/members?limit=80`),
          fetch(`/api/backend/guilds/${guildId}`),
        ]);

        if (roRes.ok) setRoles(await roRes.json());
        if (memRes.ok) {
          const mems: Member[] = await memRes.json();
          const filtered = mems.filter((m) => !m.bot);
          setMembers(filtered);
          if (filtered.length > 0) {
            setTargetUserId(filtered[0].id);
          }
        }
        if (gRes.ok) setGuildInfo(await gRes.json());
      } catch {
        setToast({ type: "error", message: "Failed to load roles and server members" });
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [guildId]);

  const selectedMember = members.find((m) => m.id === (manualUserId.trim() || targetUserId));
  const selectedRole = roles.find((r) => r.id === targetRoleId);

  const handleDispatchDM = async () => {
    const resolvedTargetId =
      targetType === "user"
        ? (manualUserId.trim() || targetUserId)
        : targetRoleId;

    if (!resolvedTargetId) {
      setToast({
        type: "error",
        message: targetType === "user" ? "Please select or enter a recipient Member ID" : "Please select a target Role",
      });
      return;
    }

    if (!content.trim()) {
      setToast({ type: "error", message: "Message content cannot be empty" });
      return;
    }

    if (targetType === "role") {
      const confirmBroadcast = window.confirm(
        `Are you sure you want to broadcast this DM to all members of @${selectedRole?.name || "role"}? Members with DMs enabled will receive a direct notification.`
      );
      if (!confirmBroadcast) return;
    }

    try {
      setDispatching(true);

      const payload = {
        target_type: targetType,
        target_id: resolvedTargetId,
        title: title.trim() || undefined,
        content: content.trim(),
        color: color,
        banner_url: bannerUrl.trim() || undefined,
        button_label: buttonUrl.trim() ? buttonLabel.trim() || "Visit Link" : undefined,
        button_url: buttonUrl.trim() || undefined,
      };

      const res = await fetch(`/api/backend/guilds/${guildId}/dm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || data.error || "Failed to dispatch DM");
      }

      setToast({
        type: "success",
        message: data.message || "Direct message dispatched successfully",
      });
    } catch (err: any) {
      setToast({ type: "error", message: err.message || "Failed to deliver DM" });
    } finally {
      setDispatching(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-[1200px] mx-auto space-y-8 animate-pulse">
        <div className="h-14 bg-[var(--surface)] rounded-xl w-72" />
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          <div className="lg:col-span-7 space-y-6">
            <div className="h-36 bg-[var(--surface)] rounded-xl" />
            <div className="h-48 bg-[var(--surface)] rounded-xl" />
          </div>
          <div className="lg:col-span-5">
            <div className="h-80 bg-[var(--surface)] rounded-xl" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-[1200px] mx-auto pb-28">
      {toast && (
        <Toast
          type={toast.type}
          message={toast.message}
          onClose={() => setToast(null)}
        />
      )}

      {/* Global Page Header */}
      <PageHeader
        icon={<Send className="w-5 h-5 text-[var(--text)]" />}
        title="Direct Messages"
        description="Send private, official direct messages to specific members or broadcast notices to an entire role."
      />

      {/* 2-Column Responsive Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start pt-6">
        {/* Left Column: Form Settings (7 cols) */}
        <div className="lg:col-span-7">
          {/* Section 1: Recipient Mode & Target */}
          <Section
            title="Recipient"
            description="Choose between an individual member or an entire role broadcast."
          >
            <FieldRow label="Target Mode" helperText="Role broadcasts are automatically rate-limited to maintain server safety.">
              <SegmentedControl
                options={[
                  { value: "user", label: "Single member", icon: <User className="w-4 h-4" /> },
                  { value: "role", label: "Role broadcast", icon: <Users className="w-4 h-4" /> },
                ]}
                value={targetType}
                onChange={(val) => {
                  setTargetType(val);
                  setManualUserId("");
                }}
              />
            </FieldRow>

            {targetType === "user" ? (
              <div className="space-y-3 pt-1">
                <FieldRow label="Select Member" helperText="Choose from actively cached server members.">
                  <select
                    value={targetUserId}
                    disabled={Boolean(manualUserId.trim())}
                    onChange={(e) => setTargetUserId(e.target.value)}
                    className="w-full input-base cursor-pointer disabled:opacity-40"
                  >
                    {members.map((m) => (
                      <option key={m.id} value={m.id} className="bg-[var(--surface)] text-[var(--text)]">
                        {m.displayName} (@{m.name}) — {m.id}
                      </option>
                    ))}
                  </select>
                </FieldRow>

                {/* Custom ID toggle link */}
                <div className="pt-1">
                  {!showCustomId && !manualUserId ? (
                    <button
                      type="button"
                      onClick={() => setShowCustomId(true)}
                      className="text-[12px] text-[var(--text-muted)] hover:text-[var(--text)] underline cursor-pointer"
                    >
                      Use a custom ID
                    </button>
                  ) : (
                    <FieldRow
                      label="Custom Discord User ID"
                      helperText="Target any member ID even if not present in recent cache."
                    >
                      <div className="flex items-center gap-2">
                        <input
                          type="text"
                          value={manualUserId}
                          onChange={(e) => setManualUserId(e.target.value)}
                          placeholder="e.g. 1201050377911554061"
                          className="w-full input-base font-mono text-xs"
                        />
                        <button
                          type="button"
                          onClick={() => {
                            setManualUserId("");
                            setShowCustomId(false);
                          }}
                          className="text-[12px] text-[var(--text-muted)] hover:text-[var(--text)] shrink-0 px-2 cursor-pointer"
                        >
                          Clear
                        </button>
                      </div>
                    </FieldRow>
                  )}
                </div>
              </div>
            ) : (
              /* Role Broadcast Selection */
              <div className="space-y-3 pt-1">
                <RoleSelect
                  label="Target Role to Broadcast"
                  description="All human members with this role will receive this direct message."
                  roles={roles}
                  value={targetRoleId}
                  onChange={setTargetRoleId}
                  placeholder="Select a role..."
                />

                <div className="text-[12px] text-[var(--warning)] bg-[var(--warning)]/10 border border-[var(--warning)]/20 p-3 rounded-lg flex items-start gap-2.5">
                  <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5" />
                  <span className="leading-relaxed">
                    A 0.4s interval is enforced automatically to avoid Discord rate limits. Members with closed DMs will be safely skipped.
                  </span>
                </div>
              </div>
            )}
          </Section>

          {/* Section 2: Message Content */}
          <Section
            title="Message"
            description="Compose the subject, body text, and accent color for the message."
          >
            <FieldRow label="Subject / Title" helperText="Optional header line displayed at the top of the notification.">
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Important Notification from Server Staff"
                className="w-full input-base"
              />
            </FieldRow>

            <FieldRow label="Message Body" required helperText="Supports markdown formatting, mentions, and links.">
              <textarea
                rows={5}
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="Type your message here..."
                className="w-full bg-[var(--card)] border border-[var(--border)] rounded-lg p-3 text-[13px] text-[var(--text)] focus:outline-none focus:border-[var(--accent)] transition-colors leading-relaxed"
                required
              />
              <div className="text-right text-[12px] font-mono text-[var(--text-faint)] pt-1">
                {content.length} characters
              </div>
            </FieldRow>

            <FieldRow label="Accent Color" helperText="Select from palette presets or input a custom hex value.">
              <ColorSwatch value={color} onChange={setColor} />
            </FieldRow>
          </Section>

          {/* Section 3: Optional Media & Action Link (Collapsible Accordion) */}
          <Section
            title="Attachments & Link"
            description="Configure an optional hero banner image and an interactive button redirect."
          >
            <Accordion
              title="Banner & Action Button"
              description="Optional visual enhancements for this direct message"
              defaultOpen={Boolean(bannerUrl || buttonUrl)}
            >
              <div className="space-y-4 pt-3">
                <FieldRow label="Banner Image URL" helperText="Direct image URL (PNG, JPG, or GIF) displayed below the body.">
                  <input
                    type="url"
                    value={bannerUrl}
                    onChange={(e) => setBannerUrl(e.target.value)}
                    placeholder="https://example.com/banner.png"
                    className="w-full input-base"
                  />
                </FieldRow>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                  <FieldRow label="Button Label" helperText="Text inside the link button.">
                    <input
                      type="text"
                      value={buttonLabel}
                      onChange={(e) => setButtonLabel(e.target.value)}
                      placeholder="e.g. View Guidelines"
                      className="w-full input-base"
                    />
                  </FieldRow>

                  <FieldRow label="Button URL" helperText="Valid https link destination.">
                    <input
                      type="url"
                      value={buttonUrl}
                      onChange={(e) => setButtonUrl(e.target.value)}
                      placeholder="https://..."
                      className="w-full input-base"
                    />
                  </FieldRow>
                </div>
              </div>
            </Accordion>
          </Section>
        </div>

        {/* Right Column: Sticky Live Discord DM Preview (5 cols) */}
        <div className="lg:col-span-5 lg:sticky lg:top-24 space-y-3">
          <div className="flex items-center justify-between px-1">
            <span className="text-[12px] font-mono tracking-[0.15em] text-[var(--text-faint)] uppercase">
              RECIPIENT PREVIEW
            </span>
            <span className="text-[11px] text-[var(--text-muted)]">
              Discord Client
            </span>
          </div>

          <div className="rounded-xl border border-[var(--border)] overflow-hidden bg-[#313338] shadow-lg">
            <DiscordPreview
              mode="dm"
              recipientName={
                targetType === "role"
                  ? `@${selectedRole?.name || "Role Members"}`
                  : selectedMember?.displayName || selectedMember?.name || "Direct Message"
              }
              recipientAvatar={selectedMember?.avatar}
              serverName={guildInfo?.name || "Server"}
              serverIcon={guildInfo?.icon}
              asEmbed={true}
              title={title}
              content={content}
              color={color}
              bannerUrl={bannerUrl}
              buttonLabel={buttonLabel}
              buttonUrl={buttonUrl}
            />
          </div>
        </div>
      </div>

      {/* Sticky Bottom Dispatch Bar */}
      <StickySaveBar
        show={Boolean(content.trim())}
        isSaving={dispatching}
        onSave={handleDispatchDM}
        saveLabel={targetType === "role" ? "Broadcast to role" : "Send direct message"}
        message={
          targetType === "role"
            ? `Ready to send DM to @${selectedRole?.name || "role"}`
            : `Ready to send to ${selectedMember?.displayName || "member"}`
        }
      />
    </div>
  );
}

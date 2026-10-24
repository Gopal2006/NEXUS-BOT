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
import { Toggle } from "@/components/ui/Toggle";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { ColorSwatch } from "@/components/ui/ColorSwatch";
import { StickySaveBar } from "@/components/ui/StickySaveBar";
import { stripEmojis } from "@/lib/utils";
import {
  Sparkles,
  Send,
  LogOut,
  Tag,
  Copy,
  Check,
  Eye,
  Image as ImageIcon,
  MessageSquare,
  Shield,
  UserCheck,
} from "lucide-react";

export default function WelcomePage() {
  const params = useParams();
  const guildId = params.guildId as string;

  const [channels, setChannels] = useState<Channel[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Form State
  const [settings, setSettings] = useState({
    welcome_ch: null as string | null,
    leave_ch: null as string | null,
    welcome_msg: "Welcome {mention} to **{guild}**!",
    leave_msg: "**{name}** has left the server. Goodbye!",
    dm_enabled: 0,
    dm_message: "Welcome to **{guild}**, {mention}! Please read our rules and enjoy your stay.",
    role_id: null as string | null,
    welcome_image_url: "" as string,
    leave_image_url: "" as string,
    welcome_color: "#DDE3E8",
    welcome_format: "embed" as "embed" | "text",
    leave_format: "embed" as "embed" | "text",
  });

  const [initialSettings, setInitialSettings] = useState<any>({});
  const [copiedTag, setCopiedTag] = useState<string | null>(null);
  const [previewTab, setPreviewTab] = useState<"welcome" | "leave" | "dm">("welcome");

  const loadData = async () => {
    try {
      setLoading(true);
      const [chRes, roRes, welRes] = await Promise.all([
        fetch(`/api/backend/guilds/${guildId}/channels`),
        fetch(`/api/backend/guilds/${guildId}/roles`),
        fetch(`/api/backend/guilds/${guildId}/settings/welcome`),
      ]);

      if (chRes.ok) setChannels(await chRes.json());
      if (roRes.ok) setRoles(await roRes.json());
      if (welRes.ok) {
        const data = await welRes.json();
        const loaded = {
          welcome_ch: data.welcome_ch || null,
          leave_ch: data.leave_ch || null,
          welcome_msg: stripEmojis(data.welcome_msg || "Welcome {mention} to **{guild}**!"),
          leave_msg: stripEmojis(data.leave_msg || "**{name}** has left the server. Goodbye!"),
          dm_enabled: data.dm_enabled ? 1 : 0,
          dm_message: stripEmojis(
            data.dm_message ||
            "Welcome to **{guild}**, {mention}! Please read our rules and enjoy your stay."
          ),
          role_id: data.role_id || null,
          welcome_image_url: data.welcome_image_url || "",
          leave_image_url: data.leave_image_url || "",
          welcome_color: data.welcome_color || "#DDE3E8",
          welcome_format: (data.welcome_format as "embed" | "text") || "embed",
          leave_format: (data.leave_format as "embed" | "text") || "embed",
        };
        setSettings(loaded);
        setInitialSettings(loaded);
      }
    } catch {
      setToast({ type: "error", message: "Failed to load welcome configuration." });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [guildId]);

  const hasChanges = JSON.stringify(settings) !== JSON.stringify(initialSettings);

  const handleSave = async () => {
    try {
      setSaving(true);
      const payload = {
        welcome_ch: settings.welcome_ch || null,
        leave_ch: settings.leave_ch || null,
        welcome_msg: settings.welcome_msg,
        leave_msg: settings.leave_msg,
        dm_enabled: settings.dm_enabled ? 1 : 0,
        dm_message: settings.dm_message,
        role_id: settings.role_id || null,
        welcome_image_url: settings.welcome_image_url.trim() || null,
        leave_image_url: settings.leave_image_url.trim() || null,
        welcome_color: settings.welcome_color || "#DDE3E8",
        welcome_format: settings.welcome_format,
        leave_format: settings.leave_format,
      };

      const res = await fetch(`/api/backend/guilds/${guildId}/settings/welcome`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to save welcome settings.");
      }

      setInitialSettings(settings);
      setToast({ type: "success", message: "Onboarding settings successfully saved!" });
    } catch (err: any) {
      setToast({ type: "error", message: err.message || "Failed to save changes." });
    } finally {
      setSaving(false);
    }
  };

  const handleCopyTag = (tag: string) => {
    navigator.clipboard.writeText(tag);
    setCopiedTag(tag);
    setTimeout(() => setCopiedTag(null), 1500);
  };

  if (loading) {
    return (
      <div className="space-y-6 pb-24">
        <CardSkeleton />
        <CardSkeleton />
      </div>
    );
  }

  const welcomeActive = !!settings.welcome_ch;
  const leaveActive = !!settings.leave_ch;

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
        icon={<Sparkles className="w-5 h-5 text-[var(--ice-silver)]" />}
        title="Welcome & Onboarding"
        description="Automate member greetings, departure logs, direct messaging, and autorole assignment."
      />

      {/* Two-Column Layout: Controls on Left, Sticky Discord Preview on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column (7 cols): Configuration Cards */}
        <div className="lg:col-span-7 space-y-6">
          {/* Welcome Master Card */}
          <MasterCard
            label="WELCOME MESSAGE"
            title="Member Welcome Greeting"
            description="Broadcast automated welcome messages in a designated channel when new members join."
            enabled={welcomeActive}
            onToggle={(val) => {
              if (!val) {
                setSettings({ ...settings, welcome_ch: null });
              } else {
                const firstText = channels.find((c) => c.type === "text");
                setSettings({ ...settings, welcome_ch: firstText?.id || null });
              }
            }}
            badge={
              welcomeActive ? (
                <StatusBadge status="active" label="Broadcasting" />
              ) : (
                <StatusBadge status="off" label="Disabled" />
              )
            }
          >
            <div className="space-y-5 pt-2">
              {/* Channel Picker */}
              <div>
                <label className="text-[13px] font-medium text-[var(--ice-silver)] block mb-1.5">
                  Welcome Announcement Channel
                </label>
                <ChannelSelect
                  channels={channels}
                  value={settings.welcome_ch || ""}
                  onChange={(val) => setSettings({ ...settings, welcome_ch: val || null })}
                  placeholder="Select welcome channel..."
                />
              </div>

              {/* Message Format Mode */}
              <div>
                <label className="text-[13px] font-medium text-[var(--ice-silver)] block mb-1.5">
                  Message Format
                </label>
                <SegmentedControl
                  options={[
                    { label: "Rich Embed", value: "embed" },
                    { label: "Plain Text", value: "text" },
                  ]}
                  value={settings.welcome_format}
                  onChange={(val) => setSettings({ ...settings, welcome_format: val as any })}
                />
              </div>

              {/* Welcome Message Template */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-[13px] font-medium text-[var(--ice-silver)]">
                    Welcome Message Template
                  </label>
                  {/* Dynamic tag chips */}
                  <div className="flex items-center gap-1.5">
                    {["{mention}", "{guild}", "{name}", "{count}"].map((tag) => (
                      <button
                        key={tag}
                        type="button"
                        onClick={() => handleCopyTag(tag)}
                        className="px-2 py-0.5 rounded-md glass-soft border border-[var(--glass-border)] text-[10px] font-mono text-[var(--ice-silver)] hover:border-[var(--ice-silver)]/40 transition-colors flex items-center gap-1 cursor-pointer"
                        title="Click to copy tag"
                      >
                        {copiedTag === tag ? (
                          <Check className="w-2.5 h-2.5 text-[var(--success)]" />
                        ) : (
                          <Tag className="w-2.5 h-2.5 text-[var(--hint)]" />
                        )}
                        <span>{tag}</span>
                      </button>
                    ))}
                  </div>
                </div>
                <textarea
                  rows={3}
                  value={settings.welcome_msg}
                  onChange={(e) => setSettings({ ...settings, welcome_msg: e.target.value })}
                  placeholder="Welcome {mention} to **{guild}**!"
                  className="w-full p-3.5 glass-soft border border-[var(--glass-border)] rounded-xl text-xs font-mono text-[var(--ice-silver)] focus:outline-none focus:border-[var(--ice-silver)]/50 transition-colors resize-none"
                />
              </div>

              {/* Accent Color Swatches (if embed) */}
              {settings.welcome_format === "embed" && (
                <div>
                  <label className="text-[13px] font-medium text-[var(--ice-silver)] block mb-2">
                    Card Accent Color
                  </label>
                  <ColorSwatch
                    value={settings.welcome_color}
                    onChange={(hex) => setSettings({ ...settings, welcome_color: hex })}
                  />
                </div>
              )}

              {/* Image URL */}
              <div>
                <label className="text-[13px] font-medium text-[var(--ice-silver)] block mb-1.5">
                  Banner / Image URL (Optional)
                </label>
                <input
                  type="url"
                  value={settings.welcome_image_url}
                  onChange={(e) => setSettings({ ...settings, welcome_image_url: e.target.value })}
                  placeholder="https://example.com/welcome-banner.png"
                  className="w-full h-11 px-3.5 glass-soft border border-[var(--glass-border)] rounded-xl text-xs font-mono text-[var(--ice-silver)] focus:outline-none focus:border-[var(--ice-silver)]/50 transition-colors"
                />
              </div>

              {/* Direct Message Greeting Toggle & Fields */}
              <div className="pt-2 border-t border-[var(--glass-border)] space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-[13px] font-medium text-[var(--ice-silver)]">
                      Direct Message New Joiners
                    </div>
                    <div className="text-[12px] text-[var(--text-muted)]">
                      Deliver a private DM to the member's Discord inbox upon joining.
                    </div>
                  </div>
                  <Toggle
                    checked={!!settings.dm_enabled}
                    onChange={(val) => setSettings({ ...settings, dm_enabled: val ? 1 : 0 })}
                  />
                </div>

                {!!settings.dm_enabled && (
                  <textarea
                    rows={3}
                    value={settings.dm_message}
                    onChange={(e) => setSettings({ ...settings, dm_message: e.target.value })}
                    placeholder="Welcome to **{guild}**, {mention}! Please read our rules..."
                    className="w-full p-3.5 glass-soft border border-[var(--glass-border)] rounded-xl text-xs font-mono text-[var(--ice-silver)] focus:outline-none focus:border-[var(--ice-silver)]/50 transition-colors resize-none"
                  />
                )}
              </div>
            </div>
          </MasterCard>

          {/* Leave Master Card */}
          <MasterCard
            label="LEAVE MESSAGE"
            title="Member Leave Announcement"
            description="Log when members depart or are kicked from the server."
            enabled={leaveActive}
            onToggle={(val) => {
              if (!val) {
                setSettings({ ...settings, leave_ch: null });
              } else {
                const firstText = channels.find((c) => c.type === "text");
                setSettings({ ...settings, leave_ch: firstText?.id || null });
              }
            }}
            badge={
              leaveActive ? (
                <StatusBadge status="active" label="Logging" />
              ) : (
                <StatusBadge status="off" label="Disabled" />
              )
            }
          >
            <div className="space-y-5 pt-2">
              {/* Leave Channel Picker */}
              <div>
                <label className="text-[13px] font-medium text-[var(--ice-silver)] block mb-1.5">
                  Departure Channel
                </label>
                <ChannelSelect
                  channels={channels}
                  value={settings.leave_ch || ""}
                  onChange={(val) => setSettings({ ...settings, leave_ch: val || null })}
                  placeholder="Select departure log channel..."
                />
              </div>

              {/* Leave Format Mode */}
              <div>
                <label className="text-[13px] font-medium text-[var(--ice-silver)] block mb-1.5">
                  Message Format
                </label>
                <SegmentedControl
                  options={[
                    { label: "Rich Embed", value: "embed" },
                    { label: "Plain Text", value: "text" },
                  ]}
                  value={settings.leave_format}
                  onChange={(val) => setSettings({ ...settings, leave_format: val as any })}
                />
              </div>

              {/* Leave Message Template */}
              <div>
                <label className="text-[13px] font-medium text-[var(--ice-silver)] block mb-1.5">
                  Departure Message Template
                </label>
                <textarea
                  rows={2}
                  value={settings.leave_msg}
                  onChange={(e) => setSettings({ ...settings, leave_msg: e.target.value })}
                  placeholder="**{name}** has left the server. Goodbye!"
                  className="w-full p-3.5 glass-soft border border-[var(--glass-border)] rounded-xl text-xs font-mono text-[var(--ice-silver)] focus:outline-none focus:border-[var(--ice-silver)]/50 transition-colors resize-none"
                />
              </div>

              {/* Leave Image URL */}
              <div>
                <label className="text-[13px] font-medium text-[var(--ice-silver)] block mb-1.5">
                  Departure Image URL (Optional)
                </label>
                <input
                  type="url"
                  value={settings.leave_image_url}
                  onChange={(e) => setSettings({ ...settings, leave_image_url: e.target.value })}
                  placeholder="https://example.com/goodbye-image.png"
                  className="w-full h-11 px-3.5 glass-soft border border-[var(--glass-border)] rounded-xl text-xs font-mono text-[var(--ice-silver)] focus:outline-none focus:border-[var(--ice-silver)]/50 transition-colors"
                />
              </div>
            </div>
          </MasterCard>
        </div>

        {/* Right Column (5 cols): Sticky Discord-style Preview */}
        <div className="lg:col-span-5 lg:sticky lg:top-24 space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono tracking-[0.2em] uppercase text-[var(--hint)] font-bold">
              DISCORD LIVE PREVIEW
            </span>
            <div className="flex items-center gap-1 glass-soft p-1 rounded-xl">
              <button
                type="button"
                onClick={() => setPreviewTab("welcome")}
                className={`px-2.5 py-1 text-[11px] font-mono rounded-lg transition-colors cursor-pointer ${
                  previewTab === "welcome"
                    ? "bg-[var(--ice-silver)] text-[var(--ink)] font-bold"
                    : "text-[var(--text-muted)] hover:text-[var(--ice-silver)]"
                }`}
              >
                Welcome
              </button>
              <button
                type="button"
                onClick={() => setPreviewTab("leave")}
                className={`px-2.5 py-1 text-[11px] font-mono rounded-lg transition-colors cursor-pointer ${
                  previewTab === "leave"
                    ? "bg-[var(--ice-silver)] text-[var(--ink)] font-bold"
                    : "text-[var(--text-muted)] hover:text-[var(--ice-silver)]"
                }`}
              >
                Leave
              </button>
              <button
                type="button"
                onClick={() => setPreviewTab("dm")}
                className={`px-2.5 py-1 text-[11px] font-mono rounded-lg transition-colors cursor-pointer ${
                  previewTab === "dm"
                    ? "bg-[var(--ice-silver)] text-[var(--ink)] font-bold"
                    : "text-[var(--text-muted)] hover:text-[var(--ice-silver)]"
                }`}
              >
                DM
              </button>
            </div>
          </div>

          {/* Discord Native Theme Container (internal styling preserved) */}
          <div className="bg-[#313338] border border-[#2b2d31] rounded-2xl overflow-hidden shadow-2xl">
            {/* Discord Channel Header */}
            <div className="bg-[#2b2d31] px-4 py-3 border-b border-[#1f2023] flex items-center justify-between text-xs text-[#dbdee1] font-semibold select-none">
              <span>
                {previewTab === "dm"
                  ? "@Nexus Direct Message"
                  : previewTab === "welcome"
                  ? `#${channels.find((c) => c.id === settings.welcome_ch)?.name || "welcome"}`
                  : `#${channels.find((c) => c.id === settings.leave_ch)?.name || "goodbye"}`}
              </span>
              <span className="text-[10px] font-mono text-[#949ba4] tracking-wider uppercase">
                Simulated
              </span>
            </div>

            {/* Message Area */}
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
                    <span className="text-xs text-[#949ba4]">Today at 12:00 PM</span>
                  </div>

                  {previewTab === "welcome" ? (
                    settings.welcome_format === "embed" ? (
                      <div
                        className="bg-[#2b2d31] rounded-lg p-3.5 border-l-[4px] space-y-2.5 max-w-md shadow-md"
                        style={{ borderLeftColor: settings.welcome_color }}
                      >
                        <div className="font-bold text-sm text-white">Member Joined</div>
                        <div className="text-xs text-[#dbdee1] leading-relaxed whitespace-pre-wrap">
                          {settings.welcome_msg
                            .replace("{mention}", "@NewUser")
                            .replace("{guild}", "Community Server")
                            .replace("{name}", "NewUser")
                            .replace("{count}", "1,420")}
                        </div>
                        {settings.welcome_image_url && (
                          <img
                            src={settings.welcome_image_url}
                            alt="Welcome banner"
                            className="w-full rounded-md object-cover max-h-48 mt-2"
                            onError={(e) => ((e.target as HTMLElement).style.display = "none")}
                          />
                        )}
                      </div>
                    ) : (
                      <div className="text-xs text-[#dbdee1] leading-relaxed whitespace-pre-wrap">
                        {settings.welcome_msg
                          .replace("{mention}", "@NewUser")
                          .replace("{guild}", "Community Server")
                          .replace("{name}", "NewUser")
                          .replace("{count}", "1,420")}
                      </div>
                    )
                  ) : previewTab === "leave" ? (
                    settings.leave_format === "embed" ? (
                      <div
                        className="bg-[#2b2d31] rounded-lg p-3.5 border-l-[4px] space-y-2.5 max-w-md shadow-md"
                        style={{ borderLeftColor: "#F87171" }}
                      >
                        <div className="font-bold text-sm text-white">Member Departed</div>
                        <div className="text-xs text-[#dbdee1] leading-relaxed whitespace-pre-wrap">
                          {settings.leave_msg
                            .replace("{name}", "Member")
                            .replace("{guild}", "Community Server")}
                        </div>
                        {settings.leave_image_url && (
                          <img
                            src={settings.leave_image_url}
                            alt="Departure banner"
                            className="w-full rounded-md object-cover max-h-48 mt-2"
                            onError={(e) => ((e.target as HTMLElement).style.display = "none")}
                          />
                        )}
                      </div>
                    ) : (
                      <div className="text-xs text-[#dbdee1] leading-relaxed whitespace-pre-wrap">
                        {settings.leave_msg
                          .replace("{name}", "Member")
                          .replace("{guild}", "Community Server")}
                      </div>
                    )
                  ) : (
                    <div className="text-xs text-[#dbdee1] leading-relaxed whitespace-pre-wrap bg-[#2b2d31] p-3.5 rounded-lg border border-[#1f2023]">
                      {settings.dm_message
                        .replace("{mention}", "@NewUser")
                        .replace("{guild}", "Community Server")}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Sticky Save Bar */}
      <StickySaveBar
        hasChanges={hasChanges}
        loading={saving}
        onSave={handleSave}
        onDiscard={() => setSettings(initialSettings)}
      />
    </div>
  );
}

"use client";

import React, { useState, useEffect, useRef } from "react";
import { useParams } from "next/navigation";
import {
  Megaphone,
  Send,
  Sparkles,
  Image as ImageIcon,
  Link as LinkIcon,
  Bell,
  Upload,
  Trash2,
  Bold,
  Italic,
  Heading,
  Quote,
  Code,
  Eye,
  CheckCircle2,
} from "lucide-react";
import { ChannelSelect, Channel } from "@/components/ChannelSelect";
import { RoleSelect, Role } from "@/components/RoleSelect";
import { Toast } from "@/components/Toast";
import { CardSkeleton } from "@/components/Skeleton";
import { PageHeader } from "@/components/ui/PageHeader";
import { MasterCard } from "@/components/ui/MasterCard";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { ColorSwatch } from "@/components/ui/ColorSwatch";
import { Accordion } from "@/components/ui/Accordion";

export default function AnnouncementsPage() {
  const params = useParams();
  const guildId = params.guildId as string;

  const [channels, setChannels] = useState<Channel[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [guildInfo, setGuildInfo] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [sentSuccess, setSentSuccess] = useState(false);
  const [toast, setToast] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Form State
  const [targetChannelId, setTargetChannelId] = useState<string | null>(null);
  const [asEmbed, setAsEmbed] = useState(true);
  const [title, setTitle] = useState("Community Update & Announcements");
  const [content, setContent] = useState(
    "Welcome to our server announcement!\n\nWe are excited to share upcoming events, server upgrades, and new community perks. Check out the link below for full details."
  );
  const [color, setColor] = useState("#DDE3E8");
  const [pingType, setPingType] = useState<"none" | "@everyone" | "@here" | "role">("none");
  const [pingRoleId, setPingRoleId] = useState<string | null>(null);
  const [bannerUrl, setBannerUrl] = useState("");
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);
  const [imageSourceMode, setImageSourceMode] = useState<"upload" | "url">("upload");
  const [thumbnailUrl, setThumbnailUrl] = useState("");
  const [buttonLabel, setButtonLabel] = useState("");
  const [buttonUrl, setButtonUrl] = useState("");

  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const [chRes, roRes, gRes] = await Promise.all([
          fetch(`/api/backend/guilds/${guildId}/channels`),
          fetch(`/api/backend/guilds/${guildId}/roles`),
          fetch(`/api/backend/guilds/${guildId}`),
        ]);

        if (chRes.ok) {
          const chData: Channel[] = await chRes.json();
          setChannels(chData);
          const preferred =
            chData.find(
              (c) =>
                c.type === "text" &&
                (c.name.includes("announc") || c.name.includes("general") || c.name.includes("news"))
            ) || chData.find((c) => c.type === "text");
          if (preferred) setTargetChannelId(preferred.id);
        }

        if (roRes.ok) setRoles(await roRes.json());
        if (gRes.ok) setGuildInfo(await gRes.json());
      } catch {
        setToast({ type: "error", message: "Failed to load channels and roles" });
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [guildId]);

  const selectedChannel = channels.find((c) => c.id === targetChannelId);

  const resolvedPing =
    pingType === "role" && pingRoleId
      ? roles.find((r) => r.id === pingRoleId)?.name || "role"
      : pingType !== "none"
      ? pingType
      : undefined;

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      setToast({ type: "error", message: "Please select an image file (PNG, JPG, GIF, WEBP)." });
      return;
    }

    if (file.size > 15 * 1024 * 1024) {
      setToast({ type: "error", message: "Image exceeds 15MB size limit. Please choose a smaller image." });
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      const dataUrl = event.target?.result as string;
      setBannerUrl(dataUrl);
      setUploadedFileName(file.name);
      setToast({ type: "success", message: `Image "${file.name}" loaded successfully!` });
    };
    reader.onerror = () => {
      setToast({ type: "error", message: "Failed to read the image file." });
    };
    reader.readAsDataURL(file);
  };

  const handleRemoveImage = () => {
    setBannerUrl("");
    setUploadedFileName(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const insertFormatting = (prefix: string, suffix: string = "") => {
    const textarea = textareaRef.current;
    if (!textarea) {
      setContent((prev) => `${prev}${prefix}${suffix}`);
      return;
    }

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selected = content.substring(start, end);
    const replacement = `${prefix}${selected || "text"}${suffix}`;
    const newContent = content.substring(0, start) + replacement + content.substring(end);
    setContent(newContent);

    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(start + prefix.length, start + prefix.length + (selected ? selected.length : 4));
    }, 10);
  };

  const handleSendAnnouncement = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetChannelId) {
      setToast({ type: "error", message: "Please select a target channel" });
      return;
    }
    if (!content.trim() && !bannerUrl.trim()) {
      setToast({ type: "error", message: "Please provide either a message or an image to announce." });
      return;
    }

    try {
      setSending(true);
      const pingPayload =
        pingType === "role" ? pingRoleId : pingType !== "none" ? pingType : undefined;

      const payload = {
        channel_id: targetChannelId,
        as_embed: asEmbed,
        title: asEmbed && title.trim() ? title.trim() : undefined,
        content: content.trim(),
        color: asEmbed ? color : undefined,
        banner_url: bannerUrl.trim() || undefined,
        thumbnail_url: asEmbed && thumbnailUrl.trim() ? thumbnailUrl.trim() : undefined,
        ping: pingPayload,
        button_label: buttonUrl.trim() ? buttonLabel.trim() || "Visit Link" : undefined,
        button_url: buttonUrl.trim() || undefined,
      };

      const res = await fetch(`/api/backend/guilds/${guildId}/announce`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || data.error || "Failed to dispatch announcement");
      }

      setSentSuccess(true);
      setTimeout(() => setSentSuccess(false), 3000);

      setToast({
        type: "success",
        message: `Announcement successfully broadcast to #${data.channel_name || "channel"}!`,
      });
    } catch (err: any) {
      setToast({ type: "error", message: err.message || "Failed to send announcement" });
    } finally {
      setSending(false);
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
        icon={<Megaphone className="w-5 h-5 text-[var(--ice-silver)]" />}
        title="Announcements"
        description="Broadcast rich embeds, plain messages, role pings, and media to server channels."
      />

      {/* Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column (7 cols): Configuration Form */}
        <div className="lg:col-span-7 space-y-6">
          <form onSubmit={handleSendAnnouncement}>
            <MasterCard
              label="NEW ANNOUNCEMENT"
              title="Message Composition"
              description="Customize the destination channel, presentation style, and media attachment."
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
                    placeholder="Choose announcement channel..."
                    filterType="text"
                  />
                </div>

                {/* Presentation Style: Embed vs Plain Text */}
                <div>
                  <label className="text-[13px] font-medium text-[var(--ice-silver)] block mb-1.5">
                    Presentation Format
                  </label>
                  <SegmentedControl
                    options={[
                      { label: "Rich Embed", value: "embed" },
                      { label: "Plain Text", value: "text" },
                    ]}
                    value={asEmbed ? "embed" : "text"}
                    onChange={(val) => setAsEmbed(val === "embed")}
                  />
                </div>

                {/* Title (Embed Only) */}
                {asEmbed && (
                  <div>
                    <label className="text-[13px] font-medium text-[var(--ice-silver)] block mb-1.5">
                      Embed Title
                    </label>
                    <input
                      type="text"
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      placeholder="e.g. Major Server Update v2.0"
                      className="w-full h-11 px-3.5 glass-soft border border-[var(--glass-border)] rounded-xl text-sm text-[var(--ice-silver)] focus:outline-none focus:border-[var(--ice-silver)]/50 transition-colors"
                    />
                  </div>
                )}

                {/* Markdown Formatting Toolbar & Content Textarea */}
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="text-[13px] font-medium text-[var(--ice-silver)]">
                      Announcement Content
                    </label>
                    {/* Formatting Buttons */}
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => insertFormatting("**", "**")}
                        className="p-1.5 rounded-lg glass-soft hover:bg-[var(--ice-silver)]/10 text-[var(--ice-silver)] text-xs transition-colors cursor-pointer"
                        title="Bold"
                      >
                        <Bold className="w-3.5 h-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() => insertFormatting("*", "*")}
                        className="p-1.5 rounded-lg glass-soft hover:bg-[var(--ice-silver)]/10 text-[var(--ice-silver)] text-xs transition-colors cursor-pointer"
                        title="Italic"
                      >
                        <Italic className="w-3.5 h-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() => insertFormatting("### ")}
                        className="p-1.5 rounded-lg glass-soft hover:bg-[var(--ice-silver)]/10 text-[var(--ice-silver)] text-xs transition-colors cursor-pointer"
                        title="Heading"
                      >
                        <Heading className="w-3.5 h-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() => insertFormatting("> ")}
                        className="p-1.5 rounded-lg glass-soft hover:bg-[var(--ice-silver)]/10 text-[var(--ice-silver)] text-xs transition-colors cursor-pointer"
                        title="Quote"
                      >
                        <Quote className="w-3.5 h-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() => insertFormatting("```\n", "\n```")}
                        className="p-1.5 rounded-lg glass-soft hover:bg-[var(--ice-silver)]/10 text-[var(--ice-silver)] text-xs transition-colors cursor-pointer"
                        title="Code Block"
                      >
                        <Code className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                  <textarea
                    ref={textareaRef}
                    rows={6}
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    placeholder="Enter your announcement text here..."
                    className="w-full p-3.5 glass-soft border border-[var(--glass-border)] rounded-xl text-xs font-mono text-[var(--ice-silver)] focus:outline-none focus:border-[var(--ice-silver)]/50 transition-colors resize-none leading-relaxed"
                  />
                  <div className="flex justify-end text-[11px] text-[var(--text-faint)] mt-1 font-mono">
                    {content.length} characters
                  </div>
                </div>

                {/* Accent Color Picker (Embed Only) */}
                {asEmbed && (
                  <div>
                    <label className="text-[13px] font-medium text-[var(--ice-silver)] block mb-2">
                      Accent Color
                    </label>
                    <ColorSwatch value={color} onChange={setColor} />
                  </div>
                )}

                {/* Ping / Mention Target */}
                <div>
                  <label className="text-[13px] font-medium text-[var(--ice-silver)] block mb-1.5">
                    Mention / Notification Ping
                  </label>
                  <SegmentedControl
                    options={[
                      { label: "None", value: "none" },
                      { label: "@everyone", value: "@everyone" },
                      { label: "@here", value: "@here" },
                      { label: "Role", value: "role" },
                    ]}
                    value={pingType}
                    onChange={(val) => setPingType(val as any)}
                  />
                  {pingType === "role" && (
                    <div className="mt-3">
                      <RoleSelect
                        roles={roles}
                        value={pingRoleId || ""}
                        onChange={(val) => setPingRoleId(val || null)}
                        placeholder="Choose role to ping..."
                      />
                    </div>
                  )}
                </div>

                {/* Banner & Image Upload Mode */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-[13px] font-medium text-[var(--ice-silver)]">
                      Media & Banner Attachment
                    </label>
                    <div className="flex items-center gap-1 glass-soft p-1 rounded-xl">
                      <button
                        type="button"
                        onClick={() => setImageSourceMode("upload")}
                        className={`px-2 py-0.5 text-[11px] font-mono rounded-lg transition-colors cursor-pointer ${
                          imageSourceMode === "upload"
                            ? "bg-[var(--ice-silver)] text-[var(--ink)] font-bold"
                            : "text-[var(--text-muted)] hover:text-[var(--ice-silver)]"
                        }`}
                      >
                        Upload
                      </button>
                      <button
                        type="button"
                        onClick={() => setImageSourceMode("url")}
                        className={`px-2 py-0.5 text-[11px] font-mono rounded-lg transition-colors cursor-pointer ${
                          imageSourceMode === "url"
                            ? "bg-[var(--ice-silver)] text-[var(--ink)] font-bold"
                            : "text-[var(--text-muted)] hover:text-[var(--ice-silver)]"
                        }`}
                      >
                        URL
                      </button>
                    </div>
                  </div>

                  {imageSourceMode === "upload" ? (
                    <div>
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept="image/*"
                        onChange={handleFileUpload}
                        className="hidden"
                      />
                      {bannerUrl ? (
                        <div className="p-3 glass-soft border border-[var(--glass-border)] rounded-xl flex items-center justify-between gap-3">
                          <div className="flex items-center gap-3 overflow-hidden">
                            <img
                              src={bannerUrl}
                              alt="Attachment preview"
                              className="w-12 h-12 rounded-lg object-cover border border-[var(--glass-border)] shrink-0"
                            />
                            <div className="overflow-hidden">
                              <div className="text-xs font-mono text-[var(--ice-silver)] truncate">
                                {uploadedFileName || "Uploaded image"}
                              </div>
                              <div className="text-[11px] text-[var(--success)] flex items-center gap-1 mt-0.5">
                                <CheckCircle2 className="w-3 h-3" />
                                <span>Ready to broadcast</span>
                              </div>
                            </div>
                          </div>
                          <button
                            type="button"
                            onClick={handleRemoveImage}
                            className="p-2 glass-soft border border-[var(--error)]/30 text-[var(--error)] hover:bg-[var(--error)]/10 rounded-lg cursor-pointer transition-colors"
                            title="Remove image"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      ) : (
                        <button
                          type="button"
                          onClick={() => fileInputRef.current?.click()}
                          className="w-full p-6 glass-soft border border-dashed border-[var(--glass-border)] hover:border-[var(--ice-silver)]/40 rounded-xl flex flex-col items-center justify-center gap-2 cursor-pointer transition-colors group"
                        >
                          <Upload className="w-6 h-6 text-[var(--hint)] group-hover:text-[var(--ice-silver)] transition-colors" />
                          <span className="text-xs text-[var(--text-muted)] group-hover:text-[var(--ice-silver)] font-medium">
                            Click to upload image or banner (PNG, JPG, GIF, WEBP up to 15MB)
                          </span>
                        </button>
                      )}
                    </div>
                  ) : (
                    <input
                      type="url"
                      value={bannerUrl}
                      onChange={(e) => setBannerUrl(e.target.value)}
                      placeholder="https://example.com/announcement-banner.png"
                      className="w-full h-11 px-3.5 glass-soft border border-[var(--glass-border)] rounded-xl text-xs font-mono text-[var(--ice-silver)] focus:outline-none focus:border-[var(--ice-silver)]/50 transition-colors"
                    />
                  )}
                </div>

                {/* Link Action Accordion */}
                <Accordion title="Interactive Action Button (Optional)" icon={<LinkIcon className="w-4 h-4" />}>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
                    <div>
                      <label className="text-[12px] font-medium text-[var(--ice-silver)] block mb-1">
                        Button Label
                      </label>
                      <input
                        type="text"
                        value={buttonLabel}
                        onChange={(e) => setButtonLabel(e.target.value)}
                        placeholder="e.g. Read Full Article"
                        className="w-full h-10 px-3 glass-soft border border-[var(--glass-border)] rounded-xl text-xs text-[var(--ice-silver)] focus:outline-none focus:border-[var(--ice-silver)]/50 transition-colors"
                      />
                    </div>
                    <div>
                      <label className="text-[12px] font-medium text-[var(--ice-silver)] block mb-1">
                        Destination URL
                      </label>
                      <input
                        type="url"
                        value={buttonUrl}
                        onChange={(e) => setButtonUrl(e.target.value)}
                        placeholder="https://discord.gg/your-server"
                        className="w-full h-10 px-3 glass-soft border border-[var(--glass-border)] rounded-xl text-xs font-mono text-[var(--ice-silver)] focus:outline-none focus:border-[var(--ice-silver)]/50 transition-colors"
                      />
                    </div>
                  </div>
                </Accordion>

                {/* Primary Dispatch Action */}
                <div className="pt-3 border-t border-[var(--glass-border)]">
                  <button
                    type="submit"
                    disabled={sending}
                    className="w-full h-12 rounded-xl bg-[var(--ice-silver)] text-[var(--ink)] font-mono text-xs font-bold tracking-[0.2em] uppercase hover:opacity-90 hover:shadow-lg transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-40 shadow-md"
                  >
                    {sending ? (
                      <span className="flex items-center gap-2">
                        <span className="w-4 h-4 border-2 border-[var(--ink)] border-t-transparent rounded-full animate-spin" />
                        <span>Broadcasting to #{selectedChannel?.name || "channel"}...</span>
                      </span>
                    ) : sentSuccess ? (
                      <span className="flex items-center gap-2 text-[var(--success)]">
                        <CheckCircle2 className="w-4 h-4" />
                        <span>Broadcast Delivered</span>
                      </span>
                    ) : (
                      <span className="flex items-center gap-2">
                        <Send className="w-4 h-4" />
                        <span>Send Announcement</span>
                      </span>
                    )}
                  </button>
                </div>
              </div>
            </MasterCard>
          </form>
        </div>

        {/* Right Column (5 cols): Sticky Discord Live Simulator */}
        <div className="lg:col-span-5 lg:sticky lg:top-24 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono tracking-[0.2em] uppercase text-[var(--hint)] font-bold">
              DISCORD LIVE PREVIEW
            </span>
            <span className="text-[11px] font-mono text-[var(--text-muted)]">
              #{selectedChannel?.name || "announcements"}
            </span>
          </div>

          <div className="bg-[#313338] border border-[#2b2d31] rounded-2xl overflow-hidden shadow-2xl">
            {/* Header */}
            <div className="bg-[#2b2d31] px-4 py-3 border-b border-[#1f2023] flex items-center justify-between text-xs text-[#dbdee1] font-semibold select-none">
              <span>#{selectedChannel?.name || "announcements"}</span>
              <span className="text-[10px] font-mono text-[#949ba4] tracking-wider uppercase">
                Simulated
              </span>
            </div>

            {/* Message Body */}
            <div className="p-4 space-y-3">
              {/* Optional Ping Tag */}
              {resolvedPing && (
                <div className="text-xs text-[#5865F2] font-semibold">
                  @{resolvedPing}
                </div>
              )}

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

                  {asEmbed ? (
                    <div
                      className="bg-[#2b2d31] rounded-lg p-3.5 border-l-[4px] space-y-2.5 max-w-md shadow-md"
                      style={{ borderLeftColor: color }}
                    >
                      {title && <div className="font-bold text-sm text-white">{title}</div>}
                      <div className="text-xs text-[#dbdee1] leading-relaxed whitespace-pre-wrap">
                        {content || "Announcement text will render here..."}
                      </div>
                      {bannerUrl && (
                        <img
                          src={bannerUrl}
                          alt="Banner preview"
                          className="w-full rounded-md object-cover max-h-56 mt-2 shadow-sm"
                          onError={(e) => ((e.target as HTMLElement).style.display = "none")}
                        />
                      )}
                      {buttonUrl && (
                        <div className="pt-2">
                          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#4e5058] hover:bg-[#6d6f78] text-white text-xs font-medium rounded transition-colors select-none">
                            <span>{buttonLabel || "Visit Link"}</span>
                            <LinkIcon className="w-3 h-3" />
                          </span>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <div className="text-xs text-[#dbdee1] leading-relaxed whitespace-pre-wrap">
                        {content || "Announcement text will render here..."}
                      </div>
                      {bannerUrl && (
                        <img
                          src={bannerUrl}
                          alt="Banner preview"
                          className="w-full rounded-md object-cover max-h-56 mt-2 shadow-sm"
                          onError={(e) => ((e.target as HTMLElement).style.display = "none")}
                        />
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

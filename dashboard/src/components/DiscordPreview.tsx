"use client";

import React from "react";
import { Hash, ExternalLink, Sparkles, MessageSquare, Radio } from "lucide-react";

export interface DiscordPreviewProps {
  mode?: "announcement" | "dm";
  channelName?: string;
  serverName?: string;
  serverIcon?: string | null;
  recipientName?: string;
  recipientAvatar?: string | null;
  botName?: string;
  botAvatar?: string | null;
  asEmbed?: boolean;
  title?: string;
  content: string;
  color?: string;
  ping?: string;
  bannerUrl?: string;
  thumbnailUrl?: string;
  buttonLabel?: string;
  buttonUrl?: string;
}

export function DiscordPreview({
  mode = "announcement",
  channelName = "announcements",
  serverName = "Community Hub",
  serverIcon,
  recipientName = "Member",
  recipientAvatar,
  botName = "Nexus",
  botAvatar,
  asEmbed = true,
  title,
  content,
  color = "#5865F2",
  ping,
  bannerUrl,
  thumbnailUrl,
  buttonLabel,
  buttonUrl,
}: DiscordPreviewProps) {
  // Format formatted timestamp
  const now = new Date();
  const timeString = `Today at ${now.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}`;

  const resolvedColor = color || "#5865F2";

  return (
    <div className="flex flex-col h-full bg-[#1e1f22] border border-[#2b2d31] rounded-xl overflow-hidden shadow-2xl">
      {/* Mock Discord Window Top Bar */}
      <div className="bg-[#1f2023] px-4 py-2.5 border-b border-[#2b2d31] flex items-center justify-between select-none">
        <div className="flex items-center gap-2">
          {mode === "announcement" ? (
            <>
              <Hash className="w-5 h-5 text-gray-400" />
              <span className="font-semibold text-sm text-gray-200">
                {channelName || "announcements"}
              </span>
              <span className="text-xs text-gray-400 hidden sm:inline">
                | Official Server Announcements
              </span>
            </>
          ) : (
            <>
              <div className="relative">
                <div className="w-5 h-5 rounded-full bg-brand/30 flex items-center justify-center text-[10px] text-brand font-bold">
                  @
                </div>
              </div>
              <span className="font-semibold text-sm text-gray-200">
                {recipientName || "Direct Message"}
              </span>
            </>
          )}
        </div>

        {/* Live indicator badge */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-[11px] font-semibold text-emerald-400">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span>Discord Live Preview</span>
        </div>
      </div>

      {/* Discord Chat Area */}
      <div className="bg-[#313338] p-4 flex-1 overflow-y-auto space-y-3 font-sans">
        {/* Message Item */}
        <div className="flex items-start gap-4 hover:bg-[#2e3035]/40 p-2 rounded-lg transition-colors">
          {/* Bot Avatar */}
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-brand to-indigo-600 flex items-center justify-center text-white font-bold text-sm flex-shrink-0 shadow-md overflow-hidden">
            {botAvatar ? (
              <img
                src={botAvatar}
                alt={botName}
                className="w-full h-full object-cover"
              />
            ) : (
              <Sparkles className="w-5 h-5 text-white" />
            )}
          </div>

          {/* Message Content Body */}
          <div className="flex-1 min-w-0 space-y-1.5">
            {/* Author Header Row */}
            <div className="flex items-baseline gap-2 flex-wrap">
              <span className="font-semibold text-[15px] text-white hover:underline cursor-pointer">
                {botName}
              </span>
              <span className="bg-[#5865F2] text-white text-[10px] font-bold px-1.5 py-0.5 rounded leading-none flex items-center uppercase tracking-wide">
                APP
              </span>
              <span className="text-xs text-gray-400 select-none">
                {timeString}
              </span>
            </div>

            {/* Mention / Ping Banner */}
            {ping && ping !== "none" && (
              <div className="inline-block bg-[#5865f2]/20 hover:bg-[#5865f2]/30 text-[#c9cdfb] font-medium text-sm px-1.5 py-0.5 rounded cursor-pointer transition-colors">
                {ping.startsWith("@") ? ping : `@${ping}`}
              </div>
            )}

            {/* Plain Text Message Mode */}
            {!asEmbed ? (
              <div className="space-y-2 max-w-xl">
                {content && (
                  <div className="text-[14px] text-gray-200 leading-relaxed whitespace-pre-wrap break-words">
                    {content}
                  </div>
                )}
                {!content && !bannerUrl && (
                  <div className="text-[14px] text-gray-400 italic">
                    Start typing your announcement or upload an image to see it live...
                  </div>
                )}
                {bannerUrl && (
                  <div className="rounded-lg overflow-hidden bg-black/30 max-h-72 border border-white/10 inline-block shadow-md">
                    <img
                      src={bannerUrl}
                      alt="Attachment"
                      className="max-w-full h-auto object-cover max-h-72 rounded-lg"
                      onError={(e) => {
                        (e.target as HTMLElement).style.display = "none";
                      }}
                    />
                  </div>
                )}
              </div>
            ) : (
              /* Rich Embed Mode */
              <div
                className="mt-1 bg-[#2b2d31] rounded-md overflow-hidden border-l-[4px] max-w-xl transition-all shadow-md"
                style={{ borderLeftColor: resolvedColor }}
              >
                <div className="p-4 space-y-2.5">
                  {/* Embed Author */}
                  <div className="flex items-center gap-2 text-xs font-semibold text-gray-300">
                    {serverIcon ? (
                      <img
                        src={serverIcon}
                        alt={serverName}
                        className="w-5 h-5 rounded-full object-cover"
                      />
                    ) : (
                      <div className="w-5 h-5 rounded-full bg-brand/40 flex items-center justify-center text-[10px] text-white font-bold">
                        {serverName.charAt(0) || "N"}
                      </div>
                    )}
                    <span>
                      {mode === "announcement" ? `Announced via ${serverName}` : `Direct Message from ${serverName}`}
                    </span>
                  </div>

                  {/* Top Section with Title and Optional Thumbnail */}
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1 flex-1">
                      {title && (
                        <h4 className="font-bold text-[15px] text-white leading-snug">
                          {title}
                        </h4>
                      )}
                      {(content || !bannerUrl) && (
                        <div className="text-[13.5px] text-gray-200 leading-relaxed whitespace-pre-wrap break-words">
                          {content || "Your embed message content will appear right here in real-time..."}
                        </div>
                      )}
                    </div>

                    {thumbnailUrl && (
                      <div className="w-16 h-16 rounded overflow-hidden flex-shrink-0 bg-black/20 border border-white/5">
                        <img
                          src={thumbnailUrl}
                          alt="Thumbnail"
                          className="w-full h-full object-cover"
                          onError={(e) => {
                            (e.target as HTMLElement).style.display = "none";
                          }}
                        />
                      </div>
                    )}
                  </div>

                  {/* Full Banner Image */}
                  {bannerUrl && (
                    <div className="mt-2 rounded-md overflow-hidden bg-black/20 max-h-64 border border-white/5">
                      <img
                        src={bannerUrl}
                        alt="Banner"
                        className="w-full h-auto object-cover max-h-64"
                        onError={(e) => {
                          (e.target as HTMLElement).style.display = "none";
                        }}
                      />
                    </div>
                  )}

                  {/* Embed Footer */}
                  <div className="pt-1 flex items-center gap-2 text-[11px] text-gray-400 select-none">
                    {serverIcon && (
                      <img
                        src={serverIcon}
                        alt="Footer Icon"
                        className="w-4 h-4 rounded-full object-cover"
                      />
                    )}
                    <span>
                      {serverName} • {timeString}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Action Link Button */}
            {buttonUrl && (
              <div className="pt-2">
                <a
                  href={buttonUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.preventDefault()}
                  className="inline-flex items-center gap-1.5 bg-[#4e5058] hover:bg-[#6d6f78] text-white font-medium text-xs px-3.5 py-1.5 rounded transition-colors shadow-sm select-none cursor-pointer"
                >
                  <span>{buttonLabel || "Visit Link"}</span>
                  <ExternalLink className="w-3.5 h-3.5 text-gray-300" />
                </a>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Simulator Bottom Helper */}
      <div className="bg-[#2b2d31]/80 px-4 py-2 border-t border-[#2b2d31] flex items-center justify-between text-xs text-gray-400">
        <span>Channel: #{channelName || "general"}</span>
        <span>Theme: {resolvedColor.toUpperCase()}</span>
      </div>
    </div>
  );
}

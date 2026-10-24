"use client";

import React, { useState, useEffect, useMemo, useRef } from "react";
import { useRouter, useParams } from "next/navigation";
import {
  Search,
  LayoutDashboard,
  Settings,
  Sparkles,
  UserPlus,
  Megaphone,
  Send,
  Gavel,
  History,
  TrendingUp,
  MessageSquare,
  Gift,
  BarChart2,
  Ticket,
  Terminal,
  Server,
  ArrowRight,
  X,
} from "lucide-react";

interface PaletteItem {
  id: string;
  title: string;
  category: string;
  href: string;
  icon: React.ElementType;
  keywords?: string;
}

export function CommandPalette({
  isOpen,
  onClose,
}: {
  isOpen: boolean;
  onClose: () => void;
}) {
  const router = useRouter();
  const params = useParams();
  const guildId = params?.guildId as string | undefined;
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const baseItems: PaletteItem[] = useMemo(() => {
    if (!guildId) {
      return [
        { id: "servers", title: "Select Server", category: "Navigation", href: "/dashboard", icon: Server },
        { id: "commands", title: "Command Directory", category: "Reference", href: "/commands", icon: Terminal },
      ];
    }

    return [
      { id: "overview", title: "Server Overview", category: "Core", href: `/dashboard/${guildId}`, icon: LayoutDashboard },
      { id: "general", title: "Server Settings & Permissions", category: "Core", href: `/dashboard/${guildId}/general`, icon: Settings },
      { id: "welcome", title: "Welcome & Leave Messages", category: "Members", href: `/dashboard/${guildId}/welcome`, icon: Sparkles },
      { id: "autorole", title: "Autorole Configuration", category: "Members", href: `/dashboard/${guildId}/autorole`, icon: UserPlus },
      { id: "announcements", title: "Broadcast Announcements", category: "Broadcast", href: `/dashboard/${guildId}/announcements`, icon: Megaphone },
      { id: "dm", title: "Direct Messages (DM)", category: "Broadcast", href: `/dashboard/${guildId}/dm`, icon: Send },
      { id: "moderation", title: "Moderation Cases & Lockdown", category: "Governance", href: `/dashboard/${guildId}/moderation`, icon: Gavel },
      { id: "audit", title: "Audit & Security Logs", category: "Governance", href: `/dashboard/${guildId}/audit`, icon: History },
      { id: "leveling", title: "Leveling & XP Rewards", category: "Engagement", href: `/dashboard/${guildId}/leveling`, icon: TrendingUp },
      { id: "autoresponder", title: "Custom Autoresponders", category: "Engagement", href: `/dashboard/${guildId}/autoresponder`, icon: MessageSquare },
      { id: "giveaways", title: "Server Giveaways", category: "Engagement", href: `/dashboard/${guildId}/giveaways`, icon: Gift },
      { id: "polls", title: "Interactive Polls", category: "Engagement", href: `/dashboard/${guildId}/polls`, icon: BarChart2 },
      { id: "tickets", title: "Support Ticket Hub", category: "Engagement", href: `/dashboard/${guildId}/tickets`, icon: Ticket },
      { id: "commands", title: "Command Directory", category: "Reference", href: "/commands", icon: Terminal },
      { id: "servers", title: "Switch Server", category: "Navigation", href: "/dashboard", icon: Server },
    ];
  }, [guildId]);

  const filteredItems = useMemo(() => {
    if (!query.trim()) return baseItems;
    const q = query.toLowerCase();
    return baseItems.filter(
      (item) =>
        item.title.toLowerCase().includes(q) ||
        item.category.toLowerCase().includes(q) ||
        item.href.toLowerCase().includes(q)
    );
  }, [baseItems, query]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setQuery("");
    }
  }, [isOpen]);

  // Keyboard navigation inside palette
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) => (prev + 1) % Math.max(1, filteredItems.length));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) => (prev - 1 + filteredItems.length) % Math.max(1, filteredItems.length));
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (filteredItems[selectedIndex]) {
          router.push(filteredItems[selectedIndex].href);
          onClose();
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, selectedIndex, filteredItems, router, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4">
      {/* Dimmed backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-md animate-in fade-in duration-150"
        onClick={onClose}
      />

      {/* Palette Modal */}
      <div className="relative w-full max-w-xl glass-strong rounded-2xl shadow-2xl overflow-hidden z-10 border border-[var(--glass-border-strong)] animate-in zoom-in-95 fade-in duration-150">
        {/* Search Input Bar */}
        <div className="flex items-center gap-3 px-4 py-3.5 border-b border-[var(--glass-border)]">
          <Search className="w-5 h-5 text-[var(--text-muted)] shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search settings, controls, and commands..."
            className="w-full bg-transparent text-[14px] text-[var(--ice-silver)] placeholder-[var(--text-faint)] focus:outline-none"
          />
          {query && (
            <button
              onClick={() => setQuery("")}
              className="p-1 text-[var(--text-faint)] hover:text-[var(--ice-silver)] rounded"
            >
              <X className="w-4 h-4" />
            </button>
          )}
          <span className="text-[10px] font-mono tracking-widest text-[var(--text-faint)] uppercase px-1.5 py-0.5 rounded border border-[var(--glass-border)]">
            ESC
          </span>
        </div>

        {/* Results List */}
        <div className="max-h-80 overflow-y-auto p-2 space-y-1">
          {filteredItems.length === 0 ? (
            <div className="text-center py-8 text-xs text-[var(--text-muted)]">
              No matching pages or controls found.
            </div>
          ) : (
            filteredItems.map((item, idx) => {
              const Icon = item.icon;
              const isSelected = idx === selectedIndex;

              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => {
                    router.push(item.href);
                    onClose();
                  }}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-left transition-colors cursor-pointer select-none ${
                    isSelected
                      ? "bg-[var(--glass-bg-strong)] border border-[var(--glass-border-strong)] text-[var(--ice-silver)]"
                      : "text-[var(--text-muted)] hover:text-[var(--ice-silver)] hover:bg-[var(--tint)] border border-transparent"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg glass-soft flex items-center justify-center text-[var(--ice-silver)] shrink-0">
                      <Icon className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-[13px] font-medium text-[var(--ice-silver)]">
                        {item.title}
                      </div>
                      <div className="text-[11px] text-[var(--text-faint)]">
                        {item.category}
                      </div>
                    </div>
                  </div>

                  <ArrowRight
                    className={`w-4 h-4 text-[var(--text-faint)] transition-transform ${
                      isSelected ? "translate-x-1 text-[var(--ice-silver)]" : ""
                    }`}
                  />
                </button>
              );
            })
          )}
        </div>

        {/* Palette Footer Hints */}
        <div className="px-4 py-2 bg-black/20 border-t border-[var(--glass-border)] flex items-center justify-between text-[11px] font-mono text-[var(--text-faint)]">
          <span>Navigate with ↑ ↓</span>
          <span>Open with Enter</span>
        </div>
      </div>
    </div>
  );
}

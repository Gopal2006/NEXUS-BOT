"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSession, signOut } from "next-auth/react";
import {
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
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Server,
  LogOut,
  X,
} from "lucide-react";
import { NexusLogo } from "@/components/NexusLogo";
import { cn } from "@/lib/utils";

interface FloatingSidebarProps {
  guildId: string;
  isMobileOpen?: boolean;
  onCloseMobile?: () => void;
}

interface NavSection {
  title: string;
  items: { label: string; href: string; icon: React.ElementType }[];
}

export function FloatingSidebar({
  guildId,
  isMobileOpen = false,
  onCloseMobile,
}: FloatingSidebarProps) {
  const pathname = usePathname();
  const { data: session } = useSession();
  const [collapsed, setCollapsed] = useState(false);
  const [collapsedSections, setCollapsedSections] = useState<Record<string, boolean>>({});

  // Restore states from localStorage
  useEffect(() => {
    try {
      const savedCollapsed = localStorage.getItem("nexus_sidebar_collapsed");
      if (savedCollapsed) setCollapsed(savedCollapsed === "true");

      const savedGroups = localStorage.getItem("nexus_sidebar_groups");
      if (savedGroups) setCollapsedSections(JSON.parse(savedGroups));
    } catch {}
  }, []);

  const toggleCollapsed = () => {
    setCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem("nexus_sidebar_collapsed", String(next));
      } catch {}
      return next;
    });
  };

  const toggleSection = (title: string) => {
    setCollapsedSections((prev) => {
      const next = { ...prev, [title]: !prev[title] };
      try {
        localStorage.setItem("nexus_sidebar_groups", JSON.stringify(next));
      } catch {}
      return next;
    });
  };

  const navSections: NavSection[] = [
    {
      title: "Core",
      items: [
        { label: "Overview", href: `/dashboard/${guildId}`, icon: LayoutDashboard },
        { label: "Settings", href: `/dashboard/${guildId}/general`, icon: Settings },
      ],
    },
    {
      title: "Members",
      items: [
        { label: "Welcome & Leave", href: `/dashboard/${guildId}/welcome`, icon: Sparkles },
        { label: "Autorole", href: `/dashboard/${guildId}/autorole`, icon: UserPlus },
      ],
    },
    {
      title: "Broadcast",
      items: [
        { label: "Announcements", href: `/dashboard/${guildId}/announcements`, icon: Megaphone },
        { label: "Direct Messages", href: `/dashboard/${guildId}/dm`, icon: Send },
      ],
    },
    {
      title: "Governance",
      items: [
        { label: "Moderation", href: `/dashboard/${guildId}/moderation`, icon: Gavel },
        { label: "Audit Logs", href: `/dashboard/${guildId}/audit`, icon: History },
      ],
    },
    {
      title: "Engagement",
      items: [
        { label: "Leveling & XP", href: `/dashboard/${guildId}/leveling`, icon: TrendingUp },
        { label: "Autoresponder", href: `/dashboard/${guildId}/autoresponder`, icon: MessageSquare },
        { label: "Giveaways", href: `/dashboard/${guildId}/giveaways`, icon: Gift },
        { label: "Polls", href: `/dashboard/${guildId}/polls`, icon: BarChart2 },
        { label: "Tickets", href: `/dashboard/${guildId}/tickets`, icon: Ticket },
      ],
    },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden animate-in fade-in duration-150"
          onClick={onCloseMobile}
        />
      )}

      {/* Floating Sidebar Container */}
      <aside
        className={cn(
          "glass-strong rounded-2xl flex flex-col justify-between p-3.5 z-40 transition-all duration-300 select-none shadow-2xl border border-[var(--glass-border-strong)]",
          // Desktop: floating position with margins
          "hidden lg:flex my-4 ml-4 sm:ml-6 min-h-[calc(100vh-2rem)] sticky top-4",
          collapsed ? "w-18" : "w-64",
          // Mobile Drawer mode
          isMobileOpen && "fixed inset-y-4 left-4 z-50 flex w-72 h-[calc(100vh-2rem)] animate-in slide-in-from-left duration-200"
        )}
      >
        <div className="space-y-4 overflow-y-auto pr-1">
          {/* Top Brand & Rail Toggle */}
          <div className="flex items-center justify-between pb-3 border-b border-[var(--glass-border)]">
            <Link
              href={`/dashboard/${guildId}`}
              className="flex items-center gap-2.5 px-1 hover:opacity-90 transition-opacity"
            >
              <div className="w-8 h-8 rounded-lg glass-soft flex items-center justify-center text-[var(--ice-silver)] shrink-0 shadow-sm border border-[var(--glass-border)]">
                <NexusLogo size={18} />
              </div>
              {!collapsed && (
                <span className="font-display font-bold tracking-[0.2em] text-sm text-[var(--ice-silver)] uppercase">
                  NEXUS
                </span>
              )}
            </Link>

            {/* Desktop collapse toggle */}
            <button
              type="button"
              onClick={toggleCollapsed}
              className="hidden lg:flex p-1.5 text-[var(--text-faint)] hover:text-[var(--ice-silver)] glass-soft rounded-lg transition-colors cursor-pointer"
              title={collapsed ? "Expand sidebar" : "Collapse to icon rail"}
              aria-label={collapsed ? "Expand sidebar" : "Collapse to icon rail"}
            >
              {collapsed ? <ChevronRight className="w-3.5 h-3.5" /> : <ChevronLeft className="w-3.5 h-3.5" />}
            </button>

            {/* Mobile close button */}
            {isMobileOpen && (
              <button
                type="button"
                onClick={onCloseMobile}
                className="lg:hidden p-1.5 text-[var(--text-faint)] hover:text-[var(--ice-silver)] glass-soft rounded-lg cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* "Back to Servers" link */}
          <div>
            <Link
              href="/dashboard"
              className={cn(
                "flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-mono tracking-wider uppercase text-[var(--text-muted)] hover:text-[var(--ice-silver)] glass-soft transition-colors",
                collapsed && "justify-center px-0"
              )}
              title="Back to servers"
            >
              <Server className="w-3.5 h-3.5 shrink-0 text-[var(--text-faint)]" />
              {!collapsed && <span>Switch Server</span>}
            </Link>
          </div>

          {/* Grouped Navigation */}
          <div className="space-y-3.5 pt-1">
            {navSections.map((section) => {
              const isGroupCollapsed = !!collapsedSections[section.title];

              return (
                <div key={section.title} className="space-y-1">
                  {!collapsed && (
                    <button
                      type="button"
                      onClick={() => toggleSection(section.title)}
                      className="w-full flex items-center justify-between text-[10px] font-mono tracking-[0.18em] text-[var(--text-faint)] px-2 py-1 uppercase hover:text-[var(--text-muted)] transition-colors select-none"
                    >
                      <span>{section.title}</span>
                      <ChevronDown
                        className={cn(
                          "w-3 h-3 transition-transform duration-150",
                          isGroupCollapsed ? "-rotate-90" : "rotate-0"
                        )}
                      />
                    </button>
                  )}

                  {(!isGroupCollapsed || collapsed) && (
                    <div className="space-y-0.5">
                      {section.items.map((item) => {
                        const Icon = item.icon;
                        const isActive = pathname === item.href;

                        return (
                          <Link
                            key={item.href}
                            href={item.href}
                            onClick={() => onCloseMobile?.()}
                            title={collapsed ? item.label : undefined}
                            className={cn(
                              "flex items-center gap-3 px-3 py-2 rounded-xl text-[13px] font-medium transition-all relative group",
                              isActive
                                ? "glass-soft text-[var(--ice-silver)] shadow-sm font-semibold border border-[var(--glass-border-strong)]"
                                : "text-[var(--text-muted)] hover:text-[var(--ice-silver)] hover:bg-[var(--tint)] border border-transparent",
                              collapsed && "justify-center px-0"
                            )}
                          >
                            {/* 2px Ice Silver Active Indicator */}
                            {isActive && (
                              <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-4 bg-[var(--ice-silver)] rounded-r-full shadow-[0_0_8px_rgba(221,227,232,0.5)]" />
                            )}

                            <Icon
                              className={cn(
                                "w-4 h-4 shrink-0 transition-colors",
                                isActive
                                  ? "text-[var(--ice-silver)]"
                                  : "text-[var(--text-faint)] group-hover:text-[var(--ice-silver)]"
                              )}
                            />

                            {!collapsed && (
                              <span className="truncate">{item.label}</span>
                            )}
                          </Link>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Pinned User Card at Bottom */}
        <div className="pt-3 border-t border-[var(--glass-border)] mt-2">
          {session?.user ? (
            <div
              className={cn(
                "flex items-center justify-between p-2 rounded-xl glass-soft",
                collapsed && "justify-center p-1.5"
              )}
            >
              <div className="flex items-center gap-2.5 overflow-hidden">
                {session.user.image ? (
                  <img
                    src={session.user.image}
                    alt={session.user.name || "User"}
                    className="w-7 h-7 rounded-lg border border-[var(--glass-border)] object-cover shrink-0"
                  />
                ) : (
                  <div className="w-7 h-7 rounded-lg bg-[var(--glass-bg)] border border-[var(--glass-border)] flex items-center justify-center text-[var(--ice-silver)] font-bold text-xs shrink-0">
                    {(session.user.name || "U")[0]}
                  </div>
                )}
                {!collapsed && (
                  <div className="overflow-hidden text-left">
                    <div className="text-xs font-semibold text-[var(--ice-silver)] truncate">
                      {session.user.name}
                    </div>
                    <div className="text-[10px] text-[var(--text-faint)] font-mono">
                      Connected
                    </div>
                  </div>
                )}
              </div>

              {!collapsed && (
                <button
                  type="button"
                  onClick={() => signOut({ callbackUrl: "/" })}
                  title="Sign out"
                  className="p-1.5 text-[var(--text-faint)] hover:text-[var(--error)] rounded-lg hover:bg-[var(--tint)] transition-colors cursor-pointer"
                >
                  <LogOut className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          ) : (
            <Link
              href="/login"
              className={cn(
                "btn-primary w-full py-2 text-xs flex items-center justify-center font-semibold",
                collapsed && "px-0 text-[10px]"
              )}
            >
              {collapsed ? "Login" : "Sign In with Discord"}
            </Link>
          )}
        </div>
      </aside>
    </>
  );
}

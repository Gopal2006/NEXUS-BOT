"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Settings,
  Gavel,
  History,
  UserCheck,
  UserPlus,
  Megaphone,
  Send,
  TrendingUp,
  MessageSquare,
  Gift,
  BarChart2,
  Ticket,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Server,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface SidebarProps {
  guildId: string;
}

interface NavSection {
  title: string;
  items: { label: string; href: string; icon: React.ElementType }[];
}

export function Sidebar({ guildId }: SidebarProps) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [collapsedSections, setCollapsedSections] = useState<Record<string, boolean>>({});

  // Restore collapsed groups from localStorage
  useEffect(() => {
    try {
      const saved = localStorage.getItem("nexus_sidebar_groups");
      if (saved) {
        setCollapsedSections(JSON.parse(saved));
      }
    } catch {}
  }, []);

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
        { label: "Welcome & Leave", href: `/dashboard/${guildId}/welcome`, icon: UserCheck },
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
    <aside
      className={cn(
        "flex-shrink-0 bg-[var(--surface)] border-r border-[var(--border)] min-h-[calc(100vh-4rem)] p-3 flex flex-col justify-between transition-all duration-200 relative select-none",
        collapsed ? "w-16" : "w-64"
      )}
    >
      <div className="space-y-4">
        {/* Switch Server & Collapse Button */}
        <div className="flex items-center justify-between gap-1 pb-2 border-b border-[var(--border)]">
          {!collapsed && (
            <Link
              href="/dashboard"
              className="flex items-center gap-2 text-[12px] font-mono tracking-[0.12em] uppercase text-[var(--text-muted)] hover:text-[var(--text)] px-2 py-1.5 rounded-md hover:bg-[var(--tint)] transition-colors truncate"
            >
              <Server className="w-3.5 h-3.5 text-[var(--text-muted)] shrink-0" />
              <span className="truncate">Switch Server</span>
            </Link>
          )}

          <button
            onClick={() => setCollapsed(!collapsed)}
            className="p-1.5 text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--tint)] rounded-md transition-colors ml-auto"
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? (
              <ChevronRight className="w-4 h-4" />
            ) : (
              <ChevronLeft className="w-4 h-4" />
            )}
          </button>
        </div>

        {/* Navigation Sections */}
        {navSections.map((section) => {
          const isGroupCollapsed = !!collapsedSections[section.title];

          return (
            <div key={section.title} className="space-y-1">
              {!collapsed && (
                <button
                  type="button"
                  onClick={() => toggleSection(section.title)}
                  className="w-full flex items-center justify-between text-[11px] font-mono tracking-[0.15em] text-[var(--text-faint)] px-2 py-1 uppercase hover:text-[var(--text-muted)] transition-colors select-none"
                >
                  <span>{section.title}</span>
                  <ChevronDown
                    className={`w-3 h-3 transition-transform duration-150 ${
                      isGroupCollapsed ? "-rotate-90" : "rotate-0"
                    }`}
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
                        title={collapsed ? item.label : undefined}
                        className={cn(
                          "flex items-center gap-2.5 px-3 py-2 rounded-md text-[13px] font-medium transition-colors relative group",
                          isActive
                            ? "bg-[var(--tint)] text-[var(--text)] border-l-2 border-[var(--accent)] font-semibold"
                            : "text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--tint)] border-l-2 border-transparent",
                          collapsed && "justify-center px-0 border-l-0"
                        )}
                      >
                        <Icon
                          className={cn(
                            "w-4 h-4 shrink-0 transition-colors",
                            isActive
                              ? "text-[var(--text)]"
                              : "text-[var(--text-muted)] group-hover:text-[var(--text)]"
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

      {/* Bottom Footer Info */}
      <div className="pt-3 border-t border-[var(--border)] text-center">
        {!collapsed ? (
          <div className="text-[10px] font-mono tracking-[0.15em] text-[var(--text-faint)] uppercase">
            NEXUS CONTROL
          </div>
        ) : (
          <div className="w-1.5 h-1.5 rounded-full bg-[var(--text-faint)] mx-auto opacity-70" />
        )}
      </div>
    </aside>
  );
}

"use client";

import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useSession, signOut } from "next-auth/react";
import {
  ChevronRight,
  LogOut,
  ChevronDown,
  Terminal,
  ShieldAlert,
  Server,
  Search,
  Bell,
  Menu,
} from "lucide-react";
import { NexusWordmark } from "@/components/NexusLogo";
import { CommandPalette } from "@/components/CommandPalette";

interface FloatingTopBarProps {
  guildName?: string;
  guildIcon?: string | null;
  onToggleMobileSidebar?: () => void;
}

export function FloatingTopBar({
  guildName,
  guildIcon,
  onToggleMobileSidebar,
}: FloatingTopBarProps) {
  const { data: session } = useSession();
  const params = useParams();
  const guildId = params?.guildId as string | undefined;
  const brandHref = guildId ? `/dashboard/${guildId}` : "/dashboard";

  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [healthStatus, setHealthStatus] = useState<"checking" | "online" | "offline">("checking");
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Global Cmd/Ctrl+K shortcut
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setPaletteOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Click outside dropdown
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Health check
  useEffect(() => {
    let isMounted = true;
    async function checkHealth() {
      try {
        const res = await fetch("/api/health");
        if (res.ok) {
          const data = await res.json();
          if (isMounted) setHealthStatus(data.status === "online" ? "online" : "checking");
        } else {
          if (isMounted) setHealthStatus("offline");
        }
      } catch {
        if (isMounted) setHealthStatus("offline");
      }
    }
    checkHealth();
    const timer = setInterval(checkHealth, 20000);
    return () => {
      isMounted = false;
      clearInterval(timer);
    };
  }, []);

  const adminIds = (process.env.NEXT_PUBLIC_ADMIN_IDS || "1201050377911554061")
    .split(",")
    .map((i) => i.trim());
  const isGlobalAdmin =
    session?.user && adminIds.includes((session.user as any).id);

  return (
    <>
      <header className="sticky top-4 z-40 mx-4 sm:mx-6 mb-6 glass-strong rounded-2xl px-4 sm:px-6 py-3 flex items-center justify-between gap-4 border border-[var(--glass-border-strong)] shadow-xl">
        {/* Left: Mobile Menu Toggle + Wordmark & Server Breadcrumb */}
        <div className="flex items-center gap-3.5">
          {onToggleMobileSidebar && (
            <button
              type="button"
              onClick={onToggleMobileSidebar}
              className="p-2 lg:hidden text-[var(--text-muted)] hover:text-[var(--ice-silver)] glass-soft rounded-lg cursor-pointer"
              aria-label="Toggle navigation menu"
            >
              <Menu className="w-4 h-4" />
            </button>
          )}

          <Link
            href={brandHref}
            className="flex items-center gap-2 hover:opacity-90 transition-opacity"
            title="NEXUS Dashboard"
          >
            <NexusWordmark />
          </Link>

          {guildName && (
            <div className="flex items-center gap-2 text-xs text-[var(--text-muted)] pl-3 border-l border-[var(--glass-border)]">
              <ChevronRight className="w-3.5 h-3.5 text-[var(--text-faint)]" />
              <div className="flex items-center gap-2">
                {guildIcon ? (
                  <img
                    src={guildIcon}
                    alt={guildName}
                    className="w-5 h-5 rounded-md border border-[var(--glass-border)] object-cover shadow-sm"
                  />
                ) : (
                  <div className="w-5 h-5 rounded-md glass-soft flex items-center justify-center text-[10px] text-[var(--ice-silver)] font-bold">
                    {guildName[0]}
                  </div>
                )}
                <span className="font-medium text-[var(--ice-silver)] tracking-wide truncate max-w-[140px] sm:max-w-[220px]">
                  {guildName}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Center: Command Palette Trigger */}
        <div className="hidden md:flex flex-1 max-w-md mx-4">
          <button
            type="button"
            onClick={() => setPaletteOpen(true)}
            className="w-full h-9 glass-soft hover:border-[var(--glass-border-strong)] rounded-xl px-3 flex items-center justify-between text-xs text-[var(--text-muted)] hover:text-[var(--ice-silver)] transition-all cursor-pointer select-none group"
          >
            <div className="flex items-center gap-2">
              <Search className="w-3.5 h-3.5 text-[var(--text-faint)] group-hover:text-[var(--ice-silver)] transition-colors" />
              <span>Search settings and commands...</span>
            </div>
            <kbd className="text-[10px] font-mono tracking-wider text-[var(--text-faint)] bg-black/20 border border-[var(--glass-border)] px-1.5 py-0.5 rounded">
              ⌘K
            </kbd>
          </button>
        </div>

        {/* Right: Core Status Dot, Commands Link & User Menu */}
        <div className="flex items-center gap-3">
          {/* Mobile search button */}
          <button
            type="button"
            onClick={() => setPaletteOpen(true)}
            className="p-2 md:hidden text-[var(--text-muted)] hover:text-[var(--ice-silver)] glass-soft rounded-lg cursor-pointer"
            aria-label="Search"
          >
            <Search className="w-4 h-4" />
          </button>

          {/* Real-time Health Dot */}
          <div
            className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full glass-soft text-[11px] font-mono border border-[var(--glass-border)]"
            title={
              healthStatus === "online"
                ? "Core Online: Bot Gateway Healthy"
                : healthStatus === "checking"
                ? "Checking Core Status..."
                : "Core Offline: Backend Unreachable"
            }
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                healthStatus === "online"
                  ? "bg-[var(--success)]"
                  : healthStatus === "checking"
                  ? "bg-[var(--warning)] animate-pulse"
                  : "bg-[var(--error)]"
              }`}
            />
            <span
              className={`text-[10px] font-semibold uppercase ${
                healthStatus === "online"
                  ? "text-[var(--text-muted)]"
                  : healthStatus === "checking"
                  ? "text-[var(--warning)]"
                  : "text-[var(--error)]"
              }`}
            >
              {healthStatus === "online" ? "Online" : healthStatus === "checking" ? "Checking" : "Offline"}
            </span>
          </div>

          <Link
            href="/commands"
            className="text-[12px] font-mono tracking-[0.12em] uppercase text-[var(--text-muted)] hover:text-[var(--ice-silver)] transition-colors hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg hover:bg-[var(--tint)]"
          >
            <Terminal className="w-3.5 h-3.5" />
            <span>Commands</span>
          </Link>

          {/* User Menu */}
          {session?.user ? (
            <div className="relative" ref={dropdownRef}>
              <button
                type="button"
                onClick={() => setDropdownOpen((prev) => !prev)}
                className="flex items-center gap-2 p-1.5 pr-2.5 rounded-xl glass-soft hover:border-[var(--glass-border-strong)] transition-all cursor-pointer"
                aria-expanded={dropdownOpen}
                aria-label="User account menu"
              >
                {session.user.image ? (
                  <img
                    src={session.user.image}
                    alt={session.user.name || "User"}
                    className="w-6 h-6 rounded-lg border border-[var(--glass-border)] object-cover"
                  />
                ) : (
                  <div className="w-6 h-6 rounded-lg bg-[var(--glass-bg)] border border-[var(--glass-border)] flex items-center justify-center text-[var(--ice-silver)] font-semibold text-xs">
                    {(session.user.name || "U")[0]}
                  </div>
                )}
                <span className="text-[13px] font-medium text-[var(--ice-silver)] hidden sm:inline">
                  {session.user.name}
                </span>
                <ChevronDown
                  className={`w-3.5 h-3.5 text-[var(--text-muted)] transition-transform duration-150 ${
                    dropdownOpen ? "rotate-180" : ""
                  }`}
                />
              </button>

              {dropdownOpen && (
                <div className="absolute right-0 mt-2 w-52 glass-strong rounded-2xl shadow-2xl p-1.5 z-50 text-xs border border-[var(--glass-border-strong)] animate-in fade-in duration-100">
                  <div className="px-3 py-2 border-b border-[var(--glass-border)] mb-1">
                    <div className="text-[10px] font-mono tracking-[0.15em] text-[var(--text-faint)] uppercase">
                      AUTHENTICATED
                    </div>
                    <div className="font-medium text-[var(--ice-silver)] truncate mt-0.5">
                      {session.user.name}
                    </div>
                  </div>

                  <Link
                    href="/dashboard"
                    onClick={() => setDropdownOpen(false)}
                    className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-[var(--text-muted)] hover:text-[var(--ice-silver)] hover:bg-[var(--tint)] transition-colors"
                  >
                    <Server className="w-3.5 h-3.5 text-[var(--text-muted)]" />
                    <span>Switch Server</span>
                  </Link>

                  <Link
                    href="/commands"
                    onClick={() => setDropdownOpen(false)}
                    className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-[var(--text-muted)] hover:text-[var(--ice-silver)] hover:bg-[var(--tint)] transition-colors"
                  >
                    <Terminal className="w-3.5 h-3.5 text-[var(--text-muted)]" />
                    <span>Command Directory</span>
                  </Link>

                  {isGlobalAdmin && (
                    <Link
                      href="/admin"
                      onClick={() => setDropdownOpen(false)}
                      className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-[var(--warning)] hover:bg-[var(--tint)] transition-colors"
                    >
                      <ShieldAlert className="w-3.5 h-3.5" />
                      <span>Global Admin</span>
                    </Link>
                  )}

                  <div className="border-t border-[var(--glass-border)] mt-1 pt-1">
                    <button
                      type="button"
                      onClick={() => signOut({ callbackUrl: "/" })}
                      className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-[var(--error)] hover:bg-[var(--tint)] transition-colors text-left cursor-pointer"
                    >
                      <LogOut className="w-3.5 h-3.5" />
                      <span>Logout</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <Link
              href="/login"
              className="btn-primary text-xs px-3.5 py-1.5 rounded-lg"
            >
              Login
            </Link>
          )}
        </div>
      </header>

      {/* Global Command Palette Modal */}
      <CommandPalette
        isOpen={paletteOpen}
        onClose={() => setPaletteOpen(false)}
      />
    </>
  );
}

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
} from "lucide-react";
import { NexusWordmark } from "@/components/NexusLogo";

interface NavbarProps {
  guildName?: string;
  guildIcon?: string | null;
}

export function Navbar({ guildName, guildIcon }: NavbarProps) {
  const { data: session } = useSession();
  const params = useParams();
  const guildId = params?.guildId as string | undefined;
  const brandHref = guildId ? `/dashboard/${guildId}` : "/dashboard";

  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const adminIds = (process.env.NEXT_PUBLIC_ADMIN_IDS || "1201050377911554061")
    .split(",")
    .map((i) => i.trim());
  const isGlobalAdmin =
    session?.user && adminIds.includes((session.user as any).id);

  return (
    <header className="h-16 border-b border-[var(--border)] bg-[var(--surface)] sticky top-0 z-40 px-6 flex items-center justify-between">
      {/* Left: Brand Wordmark & Server Breadcrumb */}
      <div className="flex items-center gap-4">
        <Link
          href={brandHref}
          className="flex items-center gap-2 hover:opacity-90 transition-opacity"
          title="NEXUS Dashboard"
        >
          <NexusWordmark />
        </Link>

        {guildName && (
          <div className="flex items-center gap-2.5 text-xs text-[var(--text-muted)] pl-3 border-l border-[var(--border)]">
            <ChevronRight className="w-3.5 h-3.5 text-[var(--text-faint)]" />
            <div className="flex items-center gap-2">
              {guildIcon ? (
                <img
                  src={guildIcon}
                  alt={guildName}
                  className="w-5 h-5 rounded-md border border-[var(--border)] object-cover"
                />
              ) : (
                <div className="w-5 h-5 rounded-md bg-[var(--card)] border border-[var(--border)] flex items-center justify-center text-[10px] text-[var(--text)] font-bold">
                  {guildName[0]}
                </div>
              )}
              <span className="font-medium text-[var(--text)] tracking-wide truncate max-w-[180px] sm:max-w-[260px]">
                {guildName}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Right: User Avatar & Editorial Dropdown */}
      <div className="flex items-center gap-3">
        <Link
          href="/commands"
          className="text-[12px] font-mono tracking-[0.12em] uppercase text-[var(--text-muted)] hover:text-[var(--text)] transition-colors hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 rounded-md hover:bg-[var(--tint)]"
        >
          <Terminal className="w-3.5 h-3.5 text-[var(--text-muted)]" />
          <span>Commands</span>
        </Link>

        {session?.user ? (
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setDropdownOpen((prev) => !prev)}
              className="flex items-center gap-2 p-1.5 pr-2.5 rounded-lg border border-[var(--border)] bg-[var(--card)] hover:border-[var(--border-strong)] transition-all cursor-pointer"
              aria-expanded={dropdownOpen}
              aria-label="User account menu"
            >
              {session.user.image ? (
                <img
                  src={session.user.image}
                  alt={session.user.name || "User"}
                  className="w-6 h-6 rounded-md border border-[var(--border)] object-cover"
                />
              ) : (
                <div className="w-6 h-6 rounded-md bg-[var(--surface)] border border-[var(--border)] flex items-center justify-center text-[var(--text)] font-semibold text-xs">
                  {(session.user.name || "U")[0]}
                </div>
              )}
              <span className="text-[13px] font-medium text-[var(--text)] hidden sm:inline tracking-normal">
                {session.user.name}
              </span>
              <ChevronDown
                className={`w-3.5 h-3.5 text-[var(--text-muted)] transition-transform duration-150 ${
                  dropdownOpen ? "rotate-180" : ""
                }`}
              />
            </button>

            {dropdownOpen && (
              <div className="absolute right-0 mt-2 w-52 rounded-xl bg-[var(--surface)] border border-[var(--border-strong)] shadow-xl p-1.5 z-50 text-xs animate-in fade-in duration-100">
                <div className="px-3 py-2 border-b border-[var(--border)] mb-1">
                  <div className="text-[10px] font-mono tracking-[0.15em] text-[var(--text-faint)] uppercase">
                    AUTHENTICATED
                  </div>
                  <div className="font-medium text-[var(--text)] truncate mt-0.5">
                    {session.user.name}
                  </div>
                </div>

                <Link
                  href="/dashboard"
                  onClick={() => setDropdownOpen(false)}
                  className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--tint)] transition-colors"
                >
                  <Server className="w-3.5 h-3.5 text-[var(--text-muted)]" />
                  <span>Switch Server</span>
                </Link>

                <Link
                  href="/commands"
                  onClick={() => setDropdownOpen(false)}
                  className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--tint)] transition-colors"
                >
                  <Terminal className="w-3.5 h-3.5 text-[var(--text-muted)]" />
                  <span>Commands Directory</span>
                </Link>

                {isGlobalAdmin && (
                  <Link
                    href="/admin"
                    onClick={() => setDropdownOpen(false)}
                    className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-[var(--warning)] hover:bg-[var(--tint)] transition-colors"
                  >
                    <ShieldAlert className="w-3.5 h-3.5" />
                    <span>Global Admin</span>
                  </Link>
                )}

                <div className="border-t border-[var(--border)] mt-1 pt-1">
                  <button
                    onClick={() => signOut({ callbackUrl: "/" })}
                    className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-[var(--error)] hover:bg-[var(--tint)] transition-colors text-left cursor-pointer"
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
  );
}

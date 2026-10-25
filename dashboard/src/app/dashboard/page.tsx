"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import { ArrowRight, AlertCircle, Users, Server, ShieldAlert } from "lucide-react";
import { BackgroundAurora } from "@/components/BackgroundAurora";
import { FloatingTopBar } from "@/components/FloatingTopBar";
import { Skeleton } from "@/components/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { stripEmojis } from "@/lib/utils";

interface Guild {
  id: string;
  name: string;
  icon: string | null;
  member_count: number;
  owner_id: string;
  is_owner: boolean;
}

export default function ServerPickerPage() {
  const { data: session } = useSession();
  const [guilds, setGuilds] = useState<Guild[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadGuilds() {
      try {
        setLoading(true);
        const res = await fetch("/api/backend/me/guilds");
        if (!res.ok) {
          const errData = await res.json().catch(() => null);
          const detail = errData?.detail || errData?.error || `Failed to retrieve servers (${res.status})`;
          throw new Error(detail);
        }
        const data = await res.json();
        setGuilds(data);
      } catch (err: any) {
        setError(err.message || "Unable to connect to NEXUS API cluster");
      } finally {
        setLoading(false);
      }
    }
    loadGuilds();
  }, []);

  const adminIds = (process.env.NEXT_PUBLIC_ADMIN_IDS || "1201050377911554061")
    .split(",")
    .map((i) => i.trim());
  const isGlobalAdmin =
    session?.user && adminIds.includes((session.user as any).id);

  const cleanName = (name: string) => stripEmojis(name) || name;

  return (
    <div className="min-h-screen bg-[var(--bg-deep)] text-[var(--ice-silver)] font-sans relative overflow-x-hidden">
      <BackgroundAurora />

      {/* Floating Top Bar */}
      <FloatingTopBar />

      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8 relative z-10">
        {/* Top Header */}
        <div className="mb-10">
          {isGlobalAdmin && (
            <div className="mb-8 p-5 rounded-2xl glass-strong border border-[var(--warning)]/30 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-xl">
              <div className="flex items-center gap-3.5">
                <div className="w-10 h-10 rounded-xl glass-soft border border-[var(--warning)]/40 flex items-center justify-center text-[var(--warning)]">
                  <ShieldAlert className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-[10px] font-mono tracking-[0.2em] uppercase text-[var(--warning)] font-bold">
                    GLOBAL ADMINISTRATOR PRIVILEGE
                  </div>
                  <div className="text-xs text-[var(--text-muted)] mt-0.5">
                    Master access active across all guilds and backend worker clusters.
                  </div>
                </div>
              </div>
              <Link
                href="/admin"
                className="px-4 py-2 bg-[var(--warning)] hover:brightness-110 text-[var(--ink)] font-bold text-xs tracking-wider uppercase font-mono rounded-xl transition-all shadow-md shrink-0 flex items-center gap-1.5"
              >
                <span>Open Admin Console</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          )}
          <h1 className="font-display font-bold text-3xl sm:text-4xl text-[var(--ice-silver)] tracking-tight mb-2">
            Servers
          </h1>
          <p className="text-xs sm:text-sm text-[var(--text-muted)] font-sans max-w-xl">
            Select an authorized guild where you are the Server Owner or hold the designated Bot-Role to manage operations.
          </p>
        </div>

        {error && (
          <div className="p-4 glass-soft border border-[var(--error)]/30 rounded-2xl flex items-center gap-3 text-[var(--error)] text-xs mb-8">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error} — Verify backend service status.</span>
          </div>
        )}

        {/* Server Grid */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="glass rounded-2xl p-6 space-y-4">
                <div className="flex items-center gap-3.5">
                  <Skeleton className="w-14 h-14 rounded-2xl" />
                  <div className="space-y-2 flex-1">
                    <Skeleton className="w-32 h-4" />
                    <Skeleton className="w-20 h-3" />
                  </div>
                </div>
                <Skeleton className="w-full h-11 rounded-xl" />
              </div>
            ))}
          </div>
        ) : guilds.length === 0 ? (
          <div className="glass-strong rounded-2xl p-8 max-w-md mx-auto">
            <EmptyState
              icon={<Server className="w-8 h-8 text-[var(--hint)]" />}
              title="No Authorized Servers"
              description="No guilds found matching your current ownership or Bot-Role credentials on this account."
            />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {guilds.map((g) => {
              const displayName = cleanName(g.name);
              return (
                <div
                  key={g.id}
                  className="glass rounded-2xl p-6 flex flex-col justify-between group transition-all duration-300 hover:-translate-y-1 hover:border-[var(--ice-silver)]/30 hover:shadow-2xl relative overflow-hidden"
                >
                  <div className="sheen" />
                  <div>
                    <div className="flex items-center gap-4 mb-6">
                      {g.icon ? (
                        <img
                          src={g.icon}
                          alt={displayName}
                          className="w-14 h-14 rounded-2xl border border-[var(--glass-border)] shadow-md object-cover"
                        />
                      ) : (
                        <div className="w-14 h-14 rounded-2xl glass-soft border border-[var(--glass-border)] flex items-center justify-center font-display font-bold text-lg text-[var(--ice-silver)]">
                          {displayName[0]?.toUpperCase() || "S"}
                        </div>
                      )}
                      <div className="overflow-hidden">
                        <h3 className="font-display font-bold text-base text-[var(--ice-silver)] truncate group-hover:text-[var(--ice-silver)] transition-colors">
                          {displayName}
                        </h3>
                        <div className="flex items-center gap-2 text-xs text-[var(--text-muted)] mt-1">
                          <Users className="w-3.5 h-3.5 text-[var(--text-faint)]" />
                          <span>{g.member_count.toLocaleString()} members</span>
                          {g.is_owner && (
                            <span className="px-2 py-0.5 rounded-full glass-soft border border-[var(--ice-silver)]/20 text-[var(--ice-silver)] text-[10px] font-mono tracking-wider uppercase font-semibold">
                              Owner
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>

                  <Link
                    href={`/dashboard/${g.id}`}
                    className="w-full group/btn relative inline-flex items-center justify-between px-4 py-3 rounded-xl border border-[var(--glass-border)] glass-soft hover:bg-[var(--ice-silver)] text-[var(--ice-silver)] hover:text-[var(--ink)] transition-all duration-300 text-xs font-mono tracking-[0.18em] uppercase font-semibold shadow-sm"
                  >
                    <span>Manage Server</span>
                    <div className="w-6 h-6 rounded-full border border-current flex items-center justify-center transition-transform duration-300 group-hover/btn:translate-x-1">
                      <ArrowRight className="w-3.5 h-3.5" />
                    </div>
                  </Link>
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}

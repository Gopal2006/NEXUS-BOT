"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  Gavel,
  Users,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  FileText,
  Ticket,
  Activity,
  Clock,
  Settings,
  Sparkles,
} from "lucide-react";
import { Skeleton } from "@/components/Skeleton";
import { CountUp } from "@/components/ui/CountUp";
import { stripEmojis } from "@/lib/utils";

export default function GuildOverviewPage() {
  const params = useParams();
  const guildId = params.guildId as string;

  const [guild, setGuild] = useState<any>(null);
  const [settings, setSettings] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [hoveredPoint, setHoveredPoint] = useState<{ day: string; count: number; auditCount: number; x: number; y: number } | null>(null);

  useEffect(() => {
    async function loadOverview() {
      try {
        setLoading(true);
        const [gRes, sRes] = await Promise.all([
          fetch(`/api/backend/guilds/${guildId}`),
          fetch(`/api/backend/guilds/${guildId}/settings`),
        ]);

        if (gRes.ok) setGuild(await gRes.json());
        if (sRes.ok) setSettings(await sRes.json());
      } catch {
        // Handled gracefully
      } finally {
        setLoading(false);
      }
    }
    loadOverview();
  }, [guildId]);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="glass rounded-2xl p-6">
          <Skeleton className="w-48 h-8 rounded-lg mb-2" />
          <Skeleton className="w-32 h-4 rounded-md" />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="glass rounded-2xl p-5 space-y-3">
              <Skeleton className="w-24 h-3 rounded-md" />
              <Skeleton className="w-16 h-6 rounded-lg" />
              <Skeleton className="w-full h-3 rounded-md" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  const rawName = guild?.name || "Server Overview";
  const cleanGuildName = stripEmojis(rawName) || rawName;

  const hasModLog = !!settings?.mod_log_channel_id;
  const hasServerLog = !!settings?.server_log_channel_id;
  const hasActivityLog = !!settings?.activity_log_channel_id;
  const hasCmdLog = !!settings?.cmd_log_channel_id;
  const configuredLogsCount = [hasModLog, hasServerLog, hasActivityLog, hasCmdLog].filter(Boolean).length;

  // Chart telemetry points for the 7-day timeline
  // Line 1: Commands (ice-silver), Line 2: Audits (--hint: #8E6B9A)
  const telemetryData = [
    { day: "MON", count: 24, auditCount: 12, x: 40, y: 110, y2: 125 },
    { day: "TUE", count: 38, auditCount: 19, x: 130, y: 75, y2: 105 },
    { day: "WED", count: 31, auditCount: 14, x: 220, y: 95, y2: 115 },
    { day: "THU", count: 52, auditCount: 28, x: 310, y: 40, y2: 80 },
    { day: "FRI", count: 47, auditCount: 22, x: 400, y: 55, y2: 90 },
    { day: "SAT", count: 68, auditCount: 35, x: 490, y: 20, y2: 65 },
    { day: "SUN", count: 59, auditCount: 30, x: 580, y: 35, y2: 75 },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-300 font-sans">
      {/* Header Banner */}
      <div className="glass rounded-2xl p-6 sm:p-8 flex flex-col sm:flex-row sm:items-center justify-between gap-6 relative overflow-hidden">
        <div className="sheen" />
        <div className="flex items-center gap-5">
          {guild?.icon ? (
            <img
              src={guild.icon}
              alt={cleanGuildName}
              className="w-16 h-16 sm:w-20 sm:h-20 rounded-2xl border border-[var(--glass-border)] shadow-lg object-cover"
            />
          ) : (
            <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-2xl glass-soft border border-[var(--glass-border)] flex items-center justify-center font-display font-bold text-2xl text-[var(--ice-silver)]">
              {cleanGuildName[0]?.toUpperCase() || "S"}
            </div>
          )}
          <div>
            <div className="text-[10px] font-mono tracking-[0.25em] text-[var(--hint)] uppercase mb-1">
              SERVER DASHBOARD
            </div>
            <h1 className="font-display font-bold text-2xl sm:text-3xl text-[var(--ice-silver)] tracking-tight">
              {cleanGuildName}
            </h1>
            <div className="flex items-center gap-3 text-xs text-[var(--text-muted)] mt-1.5 font-mono">
              <span className="flex items-center gap-1.5">
                <Users className="w-3.5 h-3.5 text-[var(--hint)]" />
                <CountUp end={guild?.member_count || 0} /> MEMBERS
              </span>
              <span>•</span>
              <span className="tracking-wider">ID: {guildId}</span>
            </div>
          </div>
        </div>

        <Link
          href={`/dashboard/${guildId}/general`}
          className="group inline-flex items-center gap-3 px-5 py-2.5 rounded-xl border border-[var(--glass-border)] glass-soft hover:bg-[var(--ice-silver)] text-[var(--ice-silver)] hover:text-[var(--ink)] text-xs font-mono tracking-[0.2em] uppercase font-semibold transition-all duration-300 self-start sm:self-auto shadow-sm"
        >
          <Settings className="w-3.5 h-3.5" />
          <span>Configure</span>
        </Link>
      </div>

      {/* Top 4 Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Stat 1: Members */}
        <div className="glass rounded-2xl p-5 transition-all duration-300 hover:-translate-y-1 hover:border-[var(--ice-silver)]/25 hover:shadow-xl relative overflow-hidden">
          <div className="sheen" />
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-mono tracking-[0.2em] uppercase text-[var(--text-faint)]">
              TOTAL MEMBERS
            </span>
            <Users className="w-4 h-4 text-[var(--hint)]" />
          </div>
          <div className="font-display font-bold text-2xl text-[var(--ice-silver)] mb-1">
            <CountUp end={guild?.member_count || 0} />
          </div>
          <div className="text-[11px] text-[var(--text-muted)] flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--success)]" />
            <span>Active Guild Sync</span>
          </div>
        </div>

        {/* Stat 2: Bot-Role Security */}
        <div className="glass rounded-2xl p-5 transition-all duration-300 hover:-translate-y-1 hover:border-[var(--ice-silver)]/25 hover:shadow-xl relative overflow-hidden">
          <div className="sheen" />
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-mono tracking-[0.2em] uppercase text-[var(--text-faint)]">
              STAFF ROLE
            </span>
            <Gavel className="w-4 h-4 text-[var(--hint)]" />
          </div>
          <div className="font-display font-bold text-xl text-[var(--ice-silver)] mb-1 flex items-center gap-2">
            {settings?.bot_role_id ? (
              <>
                <CheckCircle2 className="w-5 h-5 text-[var(--success)]" />
                <span>Enforced</span>
              </>
            ) : (
              <>
                <AlertTriangle className="w-5 h-5 text-[var(--warning)]" />
                <span>Owner Only</span>
              </>
            )}
          </div>
          <div className="text-[11px] text-[var(--text-muted)] truncate">
            {settings?.bot_role_id ? "Staff role designated" : "No staff role assigned"}
          </div>
        </div>

        {/* Stat 3: Telemetry Latency */}
        <div className="glass rounded-2xl p-5 transition-all duration-300 hover:-translate-y-1 hover:border-[var(--ice-silver)]/25 hover:shadow-xl relative overflow-hidden">
          <div className="sheen" />
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-mono tracking-[0.2em] uppercase text-[var(--text-faint)]">
              BOT LATENCY
            </span>
            <Activity className="w-4 h-4 text-[var(--success)]" />
          </div>
          <div className="font-display font-bold text-2xl text-[var(--ice-silver)] mb-1">
            <CountUp end={18} suffix=" ms" />
          </div>
          <div className="text-[11px] text-[var(--text-muted)] flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--success)] animate-pulse" />
            <span>Gateway Operational</span>
          </div>
        </div>

        {/* Stat 4: Bot Uptime */}
        <div className="glass rounded-2xl p-5 transition-all duration-300 hover:-translate-y-1 hover:border-[var(--ice-silver)]/25 hover:shadow-xl relative overflow-hidden">
          <div className="sheen" />
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-mono tracking-[0.2em] uppercase text-[var(--text-faint)]">
              UPTIME
            </span>
            <Clock className="w-4 h-4 text-[var(--hint)]" />
          </div>
          <div className="font-display font-bold text-2xl text-[var(--ice-silver)] mb-1">
            99.98%
          </div>
          <div className="text-[11px] text-[var(--text-muted)]">
            Pycord Bot Core v2.0
          </div>
        </div>
      </div>

      {/* Telemetry Chart: Line 1 Ice Silver, Line 2 --hint, Faint Grid, Glass Tooltip */}
      <div className="glass rounded-2xl p-6 sm:p-8 relative overflow-hidden">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <div className="text-[10px] font-mono tracking-[0.25em] text-[var(--hint)] uppercase mb-1">
              ACTIVITY METRICS
            </div>
            <h2 className="font-display font-bold text-lg text-[var(--ice-silver)] tracking-tight">
              7-Day Command & Audit Volume
            </h2>
          </div>
          <div className="flex items-center gap-6 text-xs font-mono text-[var(--text-muted)]">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-sm bg-[var(--ice-silver)]" />
              <span>Commands (Line 1)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-sm bg-[var(--hint)]" />
              <span>Audits (Line 2)</span>
            </div>
          </div>
        </div>

        {/* Chart SVG */}
        <div className="w-full relative">
          <svg
            viewBox="0 0 620 160"
            className="w-full h-48 select-none"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <defs>
              <linearGradient id="silverArea" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#DDE3E8" stopOpacity="0.22" />
                <stop offset="100%" stopColor="#DDE3E8" stopOpacity="0.0" />
              </linearGradient>
              <linearGradient id="hintArea" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#8E6B9A" stopOpacity="0.18" />
                <stop offset="100%" stopColor="#8E6B9A" stopOpacity="0.0" />
              </linearGradient>
            </defs>

            {/* Faint Horizontal 1px Grid Lines (at 6-8% opacity) */}
            <line x1="20" y1="30" x2="600" y2="30" stroke="#DDE3E8" strokeOpacity="0.06" strokeWidth="1" strokeDasharray="3 3" />
            <line x1="20" y1="75" x2="600" y2="75" stroke="#DDE3E8" strokeOpacity="0.06" strokeWidth="1" strokeDasharray="3 3" />
            <line x1="20" y1="120" x2="600" y2="120" stroke="#DDE3E8" strokeOpacity="0.08" strokeWidth="1" />

            {/* Filled Area - Line 2 Hint */}
            <polygon
              points="40,125 130,105 220,115 310,80 400,90 490,65 580,75 580,120 40,120"
              fill="url(#hintArea)"
            />

            {/* Filled Area - Line 1 Ice Silver */}
            <polygon
              points="40,110 130,75 220,95 310,40 400,55 490,20 580,35 580,120 40,120"
              fill="url(#silverArea)"
            />

            {/* Smooth Connected Line 2 (--hint) */}
            <polyline
              points="40,125 130,105 220,115 310,80 400,90 490,65 580,75"
              stroke="#8E6B9A"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeDasharray="4 3"
            />

            {/* Smooth Connected Line 1 (Ice Silver) */}
            <polyline
              points="40,110 130,75 220,95 310,40 400,55 490,20 580,35"
              stroke="#DDE3E8"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />

            {/* Interactive Data Points */}
            {telemetryData.map((d, i) => (
              <g
                key={i}
                className="cursor-pointer group/point"
                onMouseEnter={() => setHoveredPoint(d)}
                onMouseLeave={() => setHoveredPoint(null)}
              >
                {/* Vertical hover guide */}
                <line
                  x1={d.x}
                  y1="20"
                  x2={d.x}
                  y2="120"
                  stroke="#DDE3E8"
                  strokeOpacity={hoveredPoint?.day === d.day ? 0.35 : 0}
                  strokeWidth="1"
                  strokeDasharray="2 2"
                />

                {/* Point 1 (Ice Silver) */}
                <circle
                  cx={d.x}
                  cy={d.y}
                  r={hoveredPoint?.day === d.day ? 6 : 4}
                  fill="#0B0709"
                  stroke="#DDE3E8"
                  strokeWidth="2"
                  className="transition-all duration-200"
                />

                {/* Point 2 (Hint) */}
                <circle
                  cx={d.x}
                  cy={d.y2}
                  r={hoveredPoint?.day === d.day ? 5 : 3}
                  fill="#0B0709"
                  stroke="#8E6B9A"
                  strokeWidth="1.5"
                  className="transition-all duration-200"
                />

                {/* Day Label */}
                <text
                  x={d.x}
                  y="142"
                  textAnchor="middle"
                  fill="#DDE3E8"
                  fillOpacity={hoveredPoint?.day === d.day ? "0.9" : "0.45"}
                  fontSize="10"
                  fontFamily="monospace"
                  letterSpacing="0.1em"
                >
                  {d.day}
                </text>
              </g>
            ))}
          </svg>

          {/* Glass Tooltip */}
          {hoveredPoint && (
            <div
              className="absolute pointer-events-none glass-strong px-3 py-2 rounded-xl text-xs font-mono shadow-2xl transition-all duration-150 z-20 border border-[var(--glass-border)]"
              style={{
                left: `${(hoveredPoint.x / 620) * 100}%`,
                top: `${(hoveredPoint.y / 160) * 100}%`,
                transform: "translate(-50%, -120%)",
              }}
            >
              <div className="font-bold text-[var(--ice-silver)] mb-1">
                {hoveredPoint.day} Activity
              </div>
              <div className="text-[var(--ice-silver)] flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--ice-silver)]" />
                <span>Commands: {hoveredPoint.count}</span>
              </div>
              <div className="text-[var(--hint)] flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--hint)]" />
                <span>Audits: {hoveredPoint.auditCount}</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Core Systems Status Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Logging System */}
        <div className="glass rounded-2xl p-6 flex flex-col justify-between group hover:-translate-y-1 transition-all duration-300 relative overflow-hidden">
          <div className="sheen" />
          <div>
            <div className="flex items-center justify-between mb-4">
              <span className="text-[10px] font-mono tracking-[0.2em] uppercase text-[var(--text-faint)]">
                AUDIT LOGS
              </span>
              <div className="w-9 h-9 rounded-xl glass-soft border border-[var(--glass-border)] flex items-center justify-center text-[var(--hint)]">
                <FileText className="w-4 h-4" />
              </div>
            </div>
            <h3 className="font-display font-bold text-base text-[var(--ice-silver)] mb-1">
              4-Channel Audit Logs
            </h3>
            <p className="text-xs text-[var(--text-muted)] mb-4 leading-relaxed">
              {configuredLogsCount === 4
                ? "Full quad-channel capture enabled: moderation, server, staff, and commands."
                : `${configuredLogsCount} of 4 channels connected. Run /setupbot or configure manually.`}
            </p>
          </div>
          <Link
            href={`/dashboard/${guildId}/general`}
            className="text-xs font-mono tracking-wider text-[var(--ice-silver)] hover:text-white transition-colors flex items-center gap-1.5 pt-2 border-t border-[var(--glass-border)]"
          >
            <span>Configure Log Routing</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {/* Support Tickets */}
        <div className="glass rounded-2xl p-6 flex flex-col justify-between group hover:-translate-y-1 transition-all duration-300 relative overflow-hidden">
          <div className="sheen" />
          <div>
            <div className="flex items-center justify-between mb-4">
              <span className="text-[10px] font-mono tracking-[0.2em] uppercase text-[var(--text-faint)]">
                SUPPORT TICKETS
              </span>
              <div className="w-9 h-9 rounded-xl glass-soft border border-[var(--glass-border)] flex items-center justify-center text-[var(--hint)]">
                <Ticket className="w-4 h-4" />
              </div>
            </div>
            <h3 className="font-display font-bold text-base text-[var(--ice-silver)] mb-1">
              Support Tickets Hub
            </h3>
            <p className="text-xs text-[var(--text-muted)] mb-4 leading-relaxed">
              {settings?.ticket_category_id
                ? "Active category bound. Interactive ticket creation buttons and HTML transcripts live."
                : "No ticket category bound. Configure tickets to deploy support panels."}
            </p>
          </div>
          <Link
            href={`/dashboard/${guildId}/tickets`}
            className="text-xs font-mono tracking-wider text-[var(--ice-silver)] hover:text-white transition-colors flex items-center gap-1.5 pt-2 border-t border-[var(--glass-border)]"
          >
            <span>Ticket Settings</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {/* Member Onboarding */}
        <div className="glass rounded-2xl p-6 flex flex-col justify-between group hover:-translate-y-1 transition-all duration-300 relative overflow-hidden">
          <div className="sheen" />
          <div>
            <div className="flex items-center justify-between mb-4">
              <span className="text-[10px] font-mono tracking-[0.2em] uppercase text-[var(--text-faint)]">
                WELCOME & LEAVE
              </span>
              <div className="w-9 h-9 rounded-xl glass-soft border border-[var(--glass-border)] flex items-center justify-center text-[var(--hint)]">
                <Sparkles className="w-4 h-4" />
              </div>
            </div>
            <h3 className="font-display font-bold text-base text-[var(--ice-silver)] mb-1">
              Welcome & Leave Cards
            </h3>
            <p className="text-xs text-[var(--text-muted)] mb-4 leading-relaxed">
              Automated greeting messages, autorole assignment, embed builder, and native media uploads.
            </p>
          </div>
          <Link
            href={`/dashboard/${guildId}/welcome`}
            className="text-xs font-mono tracking-wider text-[var(--ice-silver)] hover:text-white transition-colors flex items-center gap-1.5 pt-2 border-t border-[var(--glass-border)]"
          >
            <span>Manage Welcome</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowRight, Check, CircleAlert, Clock3, FileText, Fingerprint, MessageSquareText, Settings2, Users, UserRoundCheck } from "lucide-react";
import { Skeleton } from "@/components/Skeleton";
import { stripEmojis } from "@/lib/utils";

interface GuildInfo { id?: string; name: string; icon?: string | null; member_count?: number; }
interface GuildSettings {
  bot_role_id?: string | null;
  mod_log_channel_id?: string | null;
  server_log_channel_id?: string | null;
  activity_log_channel_id?: string | null;
  cmd_log_channel_id?: string | null;
  ticket_category_id?: string | null;
  welcome_channel_id?: string | null;
  [key: string]: unknown;
}
type Readiness = { title: string; description: string; ready: boolean; href: string; action: string };

export default function GuildOverviewPage() {
  const { guildId } = useParams<{ guildId: string }>();
  const [guild, setGuild] = useState<GuildInfo | null>(null);
  const [settings, setSettings] = useState<GuildSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    async function loadOverview() {
      setLoading(true);
      setError(null);
      try {
        const [guildRes, settingsRes] = await Promise.all([
          fetch(`/api/backend/guilds/${guildId}`),
          fetch(`/api/backend/guilds/${guildId}/settings`),
        ]);
        if (!guildRes.ok) throw new Error("Nexus could not load this server. Check your access and try again.");
        if (!settingsRes.ok) throw new Error("Server details loaded, but configuration could not be read.");
        const [guildData, settingsData] = await Promise.all([guildRes.json(), settingsRes.json()]);
        if (active) { setGuild(guildData); setSettings(settingsData); }
      } catch (e) {
        if (active) setError(e instanceof Error ? e.message : "Could not load this server.");
      } finally {
        if (active) setLoading(false);
      }
    }
    if (guildId) loadOverview();
    return () => { active = false; };
  }, [guildId]);

  if (loading) return <div className="space-y-4 py-4"><Skeleton className="h-8 w-56 rounded" /><Skeleton className="h-24 w-full rounded-xl" /><Skeleton className="h-52 w-full rounded-xl" /></div>;
  if (error || !guild || !settings) return <section className="my-8 max-w-2xl border border-[var(--error)]/40 bg-[var(--glass-bg)] rounded-xl p-5"><div className="flex gap-3"><CircleAlert className="w-5 h-5 text-[var(--error)] shrink-0" /><div><h1 className="font-display text-2xl">Server overview unavailable</h1><p className="text-sm text-[var(--text-muted)] mt-1">{error || "The server response was incomplete."}</p><button onClick={() => window.location.reload()} className="btn-secondary px-3 py-2 text-sm mt-4">Try again</button></div></div></section>;

  const name = stripEmojis(guild.name) || guild.name;
  const logChannels = [settings.mod_log_channel_id, settings.server_log_channel_id, settings.activity_log_channel_id, settings.cmd_log_channel_id];
  const configuredLogs = logChannels.filter(Boolean).length;
  const readiness: Readiness[] = [
    { title: "Staff access", description: settings.bot_role_id ? "A staff role is assigned to Nexus management." : "Management is limited to the server owner until a staff role is assigned.", ready: !!settings.bot_role_id, href: `/dashboard/${guildId}/general`, action: settings.bot_role_id ? "Review access" : "Set staff role" },
    { title: "Audit routing", description: `${configuredLogs} of 4 audit destinations are configured.`, ready: configuredLogs === 4, href: `/dashboard/${guildId}/general`, action: configuredLogs === 4 ? "Review channels" : "Configure logs" },
    { title: "Support tickets", description: settings.ticket_category_id ? "A ticket category is connected." : "No ticket category is selected yet.", ready: !!settings.ticket_category_id, href: `/dashboard/${guildId}/tickets`, action: settings.ticket_category_id ? "Open tickets" : "Set up tickets" },
    { title: "Welcome messages", description: settings.welcome_channel_id ? "A welcome channel is selected." : "Welcome messaging has no channel configured.", ready: !!settings.welcome_channel_id, href: `/dashboard/${guildId}/welcome`, action: settings.welcome_channel_id ? "Edit welcome" : "Set up welcome" },
  ];

  return (
    <div className="max-w-[1040px] mx-auto pb-16">
      <header className="py-5 sm:py-7 border-b border-[var(--glass-border)]">
        <div className="flex items-center gap-4">
          {guild.icon ? <img src={guild.icon} alt="" className="w-12 h-12 rounded-lg object-cover border border-[var(--glass-border-strong)]" /> : <div className="w-12 h-12 rounded-lg flex items-center justify-center bg-[var(--glass-bg-strong)] border border-[var(--glass-border-strong)] font-display text-2xl text-[var(--accent)]">{name.charAt(0).toUpperCase()}</div>}
          <div className="min-w-0 flex-1">
            <p className="text-[11px] font-mono text-[var(--text-faint)] uppercase tracking-[.11em]">SERVER WORKSPACE</p>
            <h1 className="font-display text-4xl sm:text-5xl leading-[.95] truncate">{name}</h1>
          </div>
          <Link href={`/dashboard/${guildId}/general`} className="btn-secondary min-h-11 px-3 sm:px-4 inline-flex items-center gap-2 text-sm"><Settings2 size={15} /><span className="hidden sm:inline">Server settings</span><span className="sm:hidden">Settings</span></Link>
        </div>
        <div className="flex items-center flex-wrap gap-x-5 gap-y-2 mt-4 text-xs text-[var(--text-muted)]">
          <span className="inline-flex items-center gap-2"><Users size={14} />{typeof guild.member_count === "number" ? <>{guild.member_count.toLocaleString()} members</> : "Member count unavailable"}</span>
          <span className="inline-flex items-center gap-2 font-mono"><span className="text-[var(--text-faint)]">SERVER ID</span>{guild.id || guildId}</span>
        </div>
      </header>

      <section className="grid lg:grid-cols-[.8fr_1.2fr] gap-8 lg:gap-14 py-8 border-b border-[var(--glass-border)]">
        <div>
          <p className="text-[11px] font-mono uppercase tracking-[.12em] text-[var(--accent)]">Readiness</p>
          <h2 className="font-display text-3xl mt-1">The basics, at a glance.</h2>
          <p className="text-sm leading-relaxed text-[var(--text-muted)] mt-2">Configuration status from this server’s current Nexus settings.</p>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="border-l-2 border-[var(--accent)] pl-3 py-1"><div className="text-xs text-[var(--text-muted)]">Audit destinations</div><strong className="font-display text-3xl">{configuredLogs}<span className="text-lg text-[var(--text-faint)]"> / 4</span></strong></div>
          <div className="border-l-2 border-[var(--glass-border-strong)] pl-3 py-1"><div className="text-xs text-[var(--text-muted)]">Staff role</div><strong className="font-display text-3xl">{settings.bot_role_id ? "Assigned" : "Owner only"}</strong></div>
        </div>
      </section>

      <section className="grid lg:grid-cols-[.8fr_1.2fr] gap-8 lg:gap-14 py-8 border-b border-[var(--glass-border)]">
        <div>
          <p className="text-[11px] font-mono uppercase tracking-[.12em] text-[var(--accent)]">Setup checklist</p>
          <h2 className="font-display text-3xl mt-1">Keep the guardrails close.</h2>
          <p className="text-sm leading-relaxed text-[var(--text-muted)] mt-2">These links open the settings or workflow for each item.</p>
        </div>
        <div className="divide-y divide-[var(--glass-border)]">
          {readiness.map((item) => <Link key={item.title} href={item.href} className="group grid grid-cols-[24px_1fr_auto] gap-3 items-center py-4 first:pt-0 last:pb-0">
            <span className={item.ready ? "text-[var(--success)]" : "text-[var(--warning)]"}>{item.ready ? <Check size={17} /> : <Clock3 size={17} />}</span>
            <span className="min-w-0"><strong className="block text-sm font-medium group-hover:text-[var(--accent)]">{item.title}</strong><span className="block text-xs text-[var(--text-muted)] mt-1 leading-relaxed">{item.description}</span></span>
            <span className="text-xs text-[var(--text-faint)] group-hover:text-[var(--ice-silver)] inline-flex items-center gap-1 whitespace-nowrap">{item.action}<ArrowRight size={13} /></span>
          </Link>)}
        </div>
      </section>

      <section className="grid lg:grid-cols-[.8fr_1.2fr] gap-8 lg:gap-14 py-8">
        <div><p className="text-[11px] font-mono uppercase tracking-[.12em] text-[var(--accent)]">Workspaces</p><h2 className="font-display text-3xl mt-1">Go straight to the work.</h2><p className="text-sm leading-relaxed text-[var(--text-muted)] mt-2">Server management stays separate from Nexus product administration.</p></div>
        <div className="grid sm:grid-cols-2 gap-x-8">
          {[
            ["Moderation", "Member actions and case history", "moderation"],
            ["Audit history", "Review dashboard activity", "audit"],
            ["Announcements", "Compose a server announcement", "announcements"],
            ["Support tickets", "Configure ticket intake", "tickets"],
            ["Welcome & leave", "Set member arrival messages", "welcome"],
            ["Leveling & XP", "Configure activity rewards", "leveling"],
          ].map(([title, detail, route]) => <Link key={route} href={`/dashboard/${guildId}/${route}`} className="group py-3 border-b border-[var(--glass-border)] flex items-start justify-between gap-3">
            <span><strong className="block text-sm font-medium group-hover:text-[var(--accent)]">{title}</strong><span className="block text-xs text-[var(--text-muted)] mt-1">{detail}</span></span><ArrowRight size={14} className="text-[var(--text-faint)] mt-1 group-hover:text-[var(--accent)]" />
          </Link>)}
        </div>
      </section>
    </div>
  );
}

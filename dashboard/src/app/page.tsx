"use client";

import Link from "next/link";
import { signIn, useSession } from "next-auth/react";
import { ArrowRight, ArrowUpRight, ShieldCheck, ListChecks, UsersRound, MessageCircle, Fingerprint } from "lucide-react";
import { useEffect, useState } from "react";
import { NexusLogo } from "@/components/NexusLogo";

export default function WelcomePage() {
  const { data: session } = useSession();
  const [health, setHealth] = useState<"checking" | "online" | "offline">("checking");

  useEffect(() => {
    let active = true;
    const check = async () => {
      try {
        const response = await fetch("/api/health");
        const data = await response.json();
        if (active) setHealth(response.ok && data.status === "online" ? "online" : "offline");
      } catch {
        if (active) setHealth("offline");
      }
    };
    check();
    const timer = window.setInterval(check, 30000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);

  const enter = () => signIn("discord", { callbackUrl: "/dashboard" });

  return (
    <div className="min-h-screen flex flex-col bg-[var(--bg-deep)]">
      <header className="max-w-[1320px] w-full mx-auto px-5 sm:px-9 py-5 flex items-center justify-between border-b border-[var(--glass-border)]">
        <Link href="/" className="flex items-center gap-3" aria-label="Nexus home">
          <span className="w-9 h-9 rounded-lg border border-[var(--glass-border-strong)] bg-[var(--glass-bg)] text-[var(--accent)] flex items-center justify-center"><NexusLogo size={21} /></span>
          <span className="leading-tight"><strong className="block text-[15px] tracking-[.12em] font-semibold">NEXUS</strong><small className="text-[11px] text-[var(--text-muted)]">Community operations</small></span>
        </Link>
        <nav aria-label="Main navigation" className="flex items-center gap-4 sm:gap-8 text-sm">
          <Link className="text-[var(--text-muted)] hover:text-[var(--ice-silver)] transition-colors" href="/commands">Command reference <ArrowUpRight className="inline w-3.5 h-3.5" /></Link>
          {session?.user
            ? <Link className="text-[var(--ice-silver)] hover:text-[var(--accent)] inline-flex items-center gap-2" href="/dashboard">Open workspace <ArrowRight size={15} /></Link>
            : <button onClick={enter} className="btn-primary px-3.5 sm:px-4 py-2 text-sm">Sign in</button>}
        </nav>
      </header>

      <main className="flex-1 max-w-[1320px] w-full mx-auto px-5 sm:px-9">
        <section className="grid lg:grid-cols-[.92fr_1.08fr] gap-10 lg:gap-16 items-center py-14 sm:py-20 lg:py-24">
          <div className="max-w-[580px]">
            <div className="flex items-center gap-2 text-[11px] text-[var(--text-muted)] font-mono uppercase tracking-[.1em] mb-6">
              <span className={`w-2 h-2 rounded-full ${health === "online" ? "bg-[var(--success)]" : health === "checking" ? "bg-[var(--warning)]" : "bg-[var(--error)]"}`} />
              {health === "online" ? "Bot connected" : health === "checking" ? "Checking bot connection" : "Bot connection unavailable"}
            </div>
            <p className="text-[11px] text-[var(--accent)] font-mono uppercase tracking-[.16em] mb-3">A working console for your Discord server</p>
            <h1 className="font-display text-[clamp(3.3rem,6.8vw,6.6rem)] leading-[.9] tracking-[-.02em] text-[var(--ice-silver)] max-w-[620px]">
              Keep the<br /><span className="text-[var(--accent)]">community</span><br />in good hands.
            </h1>
            <p className="mt-6 max-w-[490px] text-[15px] sm:text-base leading-[1.75] text-[var(--text-muted)]">
              Nexus gives owners and trusted staff one place to handle moderation, audit trails, member support and everyday server setup.
            </p>
            <div className="flex flex-col sm:flex-row gap-3 mt-8">
              {session?.user
                ? <Link href="/dashboard" className="btn-primary px-5 py-3 inline-flex justify-center items-center gap-2.5">Choose a server <ArrowRight size={16} /></Link>
                : <button onClick={enter} className="btn-primary px-5 py-3 inline-flex justify-center items-center gap-2.5">Continue with Discord <ArrowRight size={16} /></button>}
              <Link href="/commands" className="btn-secondary px-5 py-3 inline-flex justify-center items-center gap-2">Browse commands <ArrowUpRight size={15} /></Link>
            </div>
            <p className="mt-5 text-xs text-[var(--text-faint)]">Server access follows your Discord ownership and configured staff role.</p>
          </div>

          <div className="lg:pl-4">
            <div className="border border-[var(--glass-border-strong)] rounded-xl bg-[var(--glass-bg)] overflow-hidden">
              <div className="flex items-center justify-between px-4 sm:px-5 py-3 border-b border-[var(--glass-border)]">
                <span className="text-[11px] font-mono uppercase tracking-[.12em] text-[var(--text-muted)]">Command → server structure</span>
                <span className="text-[10px] font-mono text-[var(--success)]">REAL WORKFLOW</span>
              </div>
              <div className="p-5 sm:p-7">
                <div className="flex items-start gap-4">
                  <span className="mt-0.5 text-[var(--accent)]"><ListChecks size={20} /></span>
                  <div className="min-w-0">
                    <p className="text-xs text-[var(--text-muted)]">ONE-STEP AUDIT SETUP</p>
                    <h2 className="font-display text-3xl sm:text-4xl mt-1">Route the important events.</h2>
                    <p className="text-sm leading-relaxed text-[var(--text-muted)] mt-2 max-w-[540px]">The implemented <code className="text-[var(--ice-silver)] font-mono text-[13px]">/setupbot</code> command creates a private Nexus Logs category with four purpose-specific channels.</p>
                  </div>
                </div>
                <div className="mt-6 rounded-lg border border-[var(--glass-border)] bg-[var(--bg-deep)] overflow-hidden">
                  <div className="px-4 py-3 border-b border-[var(--glass-border)] flex items-center gap-2.5"><span className="w-2 h-2 rounded-full bg-[var(--success)]" /><span className="text-xs">Discord server</span><span className="text-xs text-[var(--text-faint)]">/</span><span className="text-xs text-[var(--text-muted)]">NEXUS LOGS</span></div>
                  <div className="grid sm:grid-cols-2 divide-y sm:divide-y-0 sm:divide-x divide-[var(--glass-border)]">
                    <div className="p-4 space-y-3">
                      <p className="text-[10px] font-mono tracking-[.12em] uppercase text-[var(--text-faint)]">Moderation & server</p>
                      <div className="flex items-center gap-2.5 text-sm"><ShieldCheck size={14} className="text-[var(--accent)]" /><code className="font-mono text-[13px]">#mod-logs</code></div>
                      <div className="flex items-center gap-2.5 text-sm"><ListChecks size={14} className="text-[var(--accent)]" /><code className="font-mono text-[13px]">#server-logs</code></div>
                    </div>
                    <div className="p-4 space-y-3">
                      <p className="text-[10px] font-mono tracking-[.12em] uppercase text-[var(--text-faint)]">Staff & commands</p>
                      <div className="flex items-center gap-2.5 text-sm"><UsersRound size={14} className="text-[var(--accent)]" /><code className="font-mono text-[13px]">#activity-logs</code></div>
                      <div className="flex items-center gap-2.5 text-sm"><MessageCircle size={14} className="text-[var(--accent)]" /><code className="font-mono text-[13px]">#cmd-logs</code></div>
                    </div>
                  </div>
                </div>
                <div className="mt-5 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-[var(--text-muted)]">
                  <span className="inline-flex items-center gap-1.5"><Fingerprint size={13} className="text-[var(--accent)]" /> Owner controlled</span>
                  <span>Private channels</span>
                  <span>Recorded to server settings</span>
                </div>
              </div>
              <div className="px-5 py-3 border-t border-[var(--glass-border)] bg-[var(--glass-bg-strong)] flex justify-between items-center">
                <code className="font-mono text-[13px] text-[var(--ice-silver)]">/setupbot</code>
                <Link href="/commands?cmd=setupbot" className="text-xs text-[var(--text-muted)] hover:text-[var(--ice-silver)] inline-flex items-center gap-1.5">Read command details <ArrowRight size={13} /></Link>
              </div>
            </div>
          </div>
        </section>

        <section className="grid md:grid-cols-[.8fr_1.2fr] gap-6 lg:gap-12 py-8 sm:py-10 border-t border-[var(--glass-border)]">
          <div>
            <p className="text-[11px] font-mono uppercase tracking-[.14em] text-[var(--accent)]">A clear operating model</p>
            <h2 className="font-display text-3xl sm:text-4xl mt-2">The right tool for the right role.</h2>
          </div>
          <div className="divide-y divide-[var(--glass-border)]">
            <div className="grid grid-cols-[28px_1fr] gap-3 py-3 first:pt-0"><span className="font-mono text-xs text-[var(--accent)]">01</span><p className="text-sm leading-relaxed text-[var(--text-muted)]"><strong className="text-[var(--ice-silver)] font-medium">Owners</strong> set the access boundary and choose which staff role can manage Nexus.</p></div>
            <div className="grid grid-cols-[28px_1fr] gap-3 py-3"><span className="font-mono text-xs text-[var(--accent)]">02</span><p className="text-sm leading-relaxed text-[var(--text-muted)]"><strong className="text-[var(--ice-silver)] font-medium">Moderators</strong> handle cases, logs and member workflows in the server they are authorized to manage.</p></div>
            <div className="grid grid-cols-[28px_1fr] gap-3 py-3"><span className="font-mono text-xs text-[var(--accent)]">03</span><p className="text-sm leading-relaxed text-[var(--text-muted)]"><strong className="text-[var(--ice-silver)] font-medium">Product operators</strong> use a separate restricted console for Nexus-level administration.</p></div>
          </div>
        </section>

        <section className="grid sm:grid-cols-3 gap-0 border-t border-[var(--glass-border)] py-7 sm:py-9">
          <Link href="/commands" className="group py-4 sm:pr-7 sm:border-r border-[var(--glass-border)]">
            <span className="text-[11px] font-mono text-[var(--text-faint)]">REFERENCE</span>
            <span className="mt-2 flex items-center justify-between"><strong className="font-display text-2xl group-hover:text-[var(--accent)]">Command directory</strong><ArrowUpRight size={16} className="text-[var(--text-muted)]" /></span>
            <span className="block text-sm text-[var(--text-muted)] mt-1">Find syntax, permissions and examples.</span>
          </Link>
          <div className="py-4 sm:px-7 sm:border-r border-[var(--glass-border)]">
            <span className="text-[11px] font-mono text-[var(--text-faint)]">MEMBER CARE</span>
            <strong className="block font-display text-2xl mt-2">Support & onboarding</strong>
            <span className="block text-sm text-[var(--text-muted)] mt-1">Tickets, welcome messages and automatic roles.</span>
          </div>
          <div className="py-4 sm:pl-7">
            <span className="text-[11px] font-mono text-[var(--text-faint)]">PARTICIPATION</span>
            <strong className="block font-display text-2xl mt-2">Healthy engagement</strong>
            <span className="block text-sm text-[var(--text-muted)] mt-1">Polls, giveaways, leveling and custom replies.</span>
          </div>
        </section>
      </main>

      <footer className="border-t border-[var(--glass-border)]">
        <div className="max-w-[1320px] mx-auto px-5 sm:px-9 py-4 flex flex-col sm:flex-row gap-2 justify-between text-xs text-[var(--text-faint)]">
          <span>NEXUS · Discord community operations</span><span>Access is checked against Discord and server settings.</span>
        </div>
      </footer>
    </div>
  );
}

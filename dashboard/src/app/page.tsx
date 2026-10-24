"use client";

import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { signIn, useSession } from "next-auth/react";
import { ArrowUpRight, ArrowRight } from "lucide-react";
import { NexusWordmark } from "@/components/NexusLogo";
import { CustomCursor } from "@/components/CustomCursor";

export default function WelcomePage() {
  const { data: session, status } = useSession();
  const lettersRef = useRef<(HTMLSpanElement | null)[]>([]);
  const [mounted, setMounted] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [healthStatus, setHealthStatus] = useState<"checking" | "online" | "offline">("checking");

  const mouseState = useRef({
    lastX: 0,
    lastY: 0,
    lastTime: 0,
    velocity: 0,
    smoothedVelocity: 0,
    dirX: 0,
    idleTimeout: 0,
  });

  // Health check polling for bot/API core status
  useEffect(() => {
    let isMounted = true;

    async function checkHealth() {
      try {
        const res = await fetch("/api/health");
        if (res.ok) {
          const data = await res.json();
          if (isMounted) {
            setHealthStatus(data.status === "online" ? "online" : "checking");
          }
        } else {
          if (isMounted) setHealthStatus("offline");
        }
      } catch {
        if (isMounted) setHealthStatus("offline");
      }
    }

    checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    setMounted(true);
    const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReducedMotion(motionQuery.matches);

    const handleMotionChange = (e: MediaQueryListEvent) => setReducedMotion(e.matches);
    motionQuery.addEventListener("change", handleMotionChange);

    if (motionQuery.matches) {
      return () => motionQuery.removeEventListener("change", handleMotionChange);
    }

    let rafId: number;

    const onMouseMove = (e: MouseEvent) => {
      const now = performance.now();
      const dt = Math.max(10, now - mouseState.current.lastTime);
      const dx = e.clientX - mouseState.current.lastX;
      const dy = e.clientY - mouseState.current.lastY;

      const dist = Math.sqrt(dx * dx + dy * dy);
      const instantVelocity = dist / dt;

      mouseState.current.velocity = instantVelocity;
      mouseState.current.dirX = dx !== 0 ? Math.sign(dx) : 0;
      mouseState.current.lastX = e.clientX;
      mouseState.current.lastY = e.clientY;
      mouseState.current.lastTime = now;
      mouseState.current.idleTimeout = now + 90;
    };

    window.addEventListener("mousemove", onMouseMove, { passive: true });

    const updateMotionBlur = (now: number) => {
      if (now > mouseState.current.idleTimeout) {
        mouseState.current.velocity = 0;
      }

      mouseState.current.smoothedVelocity +=
        (mouseState.current.velocity - mouseState.current.smoothedVelocity) * 0.18;

      const v = mouseState.current.smoothedVelocity;
      const blurPx = Math.min(10, v * 3.8);
      const dir = mouseState.current.dirX;

      lettersRef.current.forEach((el, idx) => {
        if (!el) return;
        if (v < 0.02) {
          el.style.filter = "none";
          el.style.transform = "none";
        } else {
          const offset = dir * Math.min(14, v * 5) * (1 + (idx - 2) * 0.12);
          el.style.filter = `blur(${blurPx.toFixed(2)}px)`;
          el.style.transform = `translateX(${offset.toFixed(2)}px)`;
        }
      });

      rafId = requestAnimationFrame(updateMotionBlur);
    };

    rafId = requestAnimationFrame(updateMotionBlur);

    return () => {
      motionQuery.removeEventListener("change", handleMotionChange);
      window.removeEventListener("mousemove", onMouseMove);
      cancelAnimationFrame(rafId);
    };
  }, []);

  const word = ["N", "E", "X", "U", "S"];

  const handleLogin = () => {
    signIn("discord", { callbackUrl: "/dashboard" });
  };

  return (
    <div
      style={{
        backgroundColor: "#0B0709",
        color: "#DDE3E8",
        ["--bg" as any]: "#0B0709",
        ["--text" as any]: "#DDE3E8",
        ["--text-muted" as any]: "rgba(221,227,232,0.60)",
        ["--text-faint" as any]: "rgba(221,227,232,0.38)",
        ["--accent" as any]: "#DDE3E8",
        ["--accent-ink" as any]: "#12040F",
        ["--border" as any]: "rgba(221,227,232,0.10)",
        ["--hint" as any]: "#8E6B9A",
      }}
      className="relative h-screen max-h-screen w-screen overflow-hidden select-none flex flex-col justify-between p-5 md:p-8 font-sans"
    >
      <CustomCursor />

      {/* Faint Film Grain Overlay (3% opacity) */}
      <div className="grain-overlay fixed inset-0 z-20 pointer-events-none" />

      {/* Subtle Ambient Glow */}
      <div
        className={`pointer-events-none absolute -top-40 left-1/2 -translate-x-1/2 w-[750px] h-[500px] rounded-full bg-gradient-to-b from-[#8E6B9A]/15 via-transparent to-transparent blur-[140px] z-0 ${reducedMotion ? "" : "animate-pulse"
          }`}
        style={{ animationDuration: "8s" }}
      />
      <div
        className="pointer-events-none absolute -bottom-48 right-1/4 w-[600px] h-[500px] rounded-full bg-[#8E6B9A]/10 blur-[150px] z-0"
      />

      {/* Faint Vertical Column Lines (3-5% opacity) */}
      <div className="pointer-events-none absolute inset-0 grid grid-cols-6 sm:grid-cols-8 md:grid-cols-10 h-full w-full z-0 px-6 md:px-10">
        {Array.from({ length: 10 }).map((_, i) => (
          <div
            key={i}
            className={`h-full border-r border-[var(--border)] ${i >= 6 ? "hidden sm:block" : ""
              } ${i >= 8 ? "hidden md:block" : ""}`}
          />
        ))}
      </div>

      {/* Top Bar */}
      <header
        className={`relative z-30 flex items-center justify-between shrink-0 transition-all duration-700 ease-out ${mounted ? "opacity-100 translate-y-0" : "opacity-0 -translate-y-4"
          }`}
      >
        <Link href="/" className="group flex items-center gap-3">
          <NexusWordmark />
        </Link>

        {/* Real Status Dot & Navigation */}
        <div className="flex items-center gap-6 md:gap-10 text-[11px] font-semibold tracking-[0.2em] text-[var(--text-muted)] uppercase">
          {/* Dynamic Core Health Dot */}
          <div className="flex items-center gap-2">
            <span
              className={`w-1.5 h-1.5 rounded-full ${healthStatus === "online"
                  ? "bg-[var(--success)]"
                  : healthStatus === "checking"
                    ? "bg-[var(--warning)] animate-pulse"
                    : "bg-[var(--error)]"
                }`}
            />
            <span
              className={`font-mono text-[10px] sm:text-[11px] ${healthStatus === "online"
                  ? "text-[var(--text)]"
                  : healthStatus === "checking"
                    ? "text-[var(--warning)]"
                    : "text-[var(--error)]"
                }`}
            >
              {healthStatus === "online"
                ? "CORE ONLINE"
                : healthStatus === "checking"
                  ? "CORE CHECKING"
                  : "CORE OFFLINE"}
            </span>
          </div>

          <Link
            href="/commands"
            className="hover:text-[var(--text)] transition-colors hidden sm:flex items-center gap-1.5"
          >
            <span>COMMANDS</span>
            <ArrowUpRight className="w-3 h-3 text-[var(--text-muted)] opacity-80" />
          </Link>

          {status === "authenticated" && (
            <Link
              href="/dashboard"
              className="text-[var(--text)] hover:underline transition-colors"
            >
              CONSOLE
            </Link>
          )}
        </div>
      </header>

      {/* Centered Editorial Hero Area */}
      <main className="relative z-30 flex-1 flex flex-col items-center justify-center my-auto py-4 text-center px-4 min-h-0">
        <div
          className={`flex flex-col items-center transition-all duration-1000 ease-out delay-150 ${mounted ? "opacity-100 translate-y-0 scale-100" : "opacity-0 translate-y-6 scale-[0.98]"
            }`}
        >
          {/* Subtle category tag */}
          <div className="mb-2 sm:mb-3 text-[10px] sm:text-[11px] font-mono tracking-[0.3em] uppercase text-[var(--hint)]">
            PRIVATE CONTROL INTERFACE
          </div>

          {/* Huge NEXUS Headline with Individual Motion-Blurred Letters */}
          <h1
            className="font-display font-black text-6xl sm:text-8xl md:text-9xl lg:text-[10rem] xl:text-[11.5rem] tracking-tighter text-[var(--text)] leading-none mb-2 sm:mb-3 select-none flex items-center justify-center"
            style={{ letterSpacing: "-0.04em" }}
          >
            {word.map((char, index) => (
              <span
                key={index}
                ref={(el) => {
                  lettersRef.current[index] = el;
                }}
                className="inline-block transition-transform duration-75 will-change-transform"
              >
                {char}
              </span>
            ))}
          </h1>

          {/* Subtitle */}
          <p className="text-xs sm:text-sm font-mono tracking-[0.28em] text-[var(--text-muted)] uppercase mb-6 sm:mb-8">
            YOUR CONTROL CENTER
          </p>

          {/* Minimal Circular Arrow Pill Button */}
          <div className="flex flex-col sm:flex-row items-center gap-4">
            {status === "authenticated" ? (
              <Link
                href="/dashboard"
                className="group relative inline-flex items-center gap-4 px-8 py-3.5 rounded-full bg-[var(--accent)] text-[var(--accent-ink)] hover:bg-white transition-all duration-200 shadow-lg cursor-pointer"
              >
                <span className="text-xs font-semibold tracking-[0.2em] uppercase font-mono">
                  Enter Dashboard
                </span>
                <div className="w-7 h-7 rounded-full border border-current flex items-center justify-center transition-transform duration-200 group-hover:translate-x-1">
                  <ArrowRight className="w-3.5 h-3.5" />
                </div>
              </Link>
            ) : (
              <button
                type="button"
                onClick={handleLogin}
                className="group relative inline-flex items-center gap-4 px-8 py-3.5 rounded-full bg-[var(--accent)] text-[var(--accent-ink)] hover:bg-white transition-all duration-200 shadow-lg cursor-pointer"
              >
                <span className="text-xs font-semibold tracking-[0.2em] uppercase font-mono">
                  Login with Discord
                </span>
                <div className="w-7 h-7 rounded-full border border-current flex items-center justify-center transition-transform duration-200 group-hover:translate-x-1">
                  <ArrowRight className="w-3.5 h-3.5" />
                </div>
              </button>
            )}
          </div>
        </div>
      </main>

      {/* Bottom Bar / Metadata with guaranteed no-overlap padding */}
      <footer
        className={`relative z-30 flex flex-col sm:flex-row items-center justify-between gap-2 text-[11px] font-mono tracking-[0.2em] text-[var(--text-faint)] uppercase pt-3 border-t border-[var(--border)] shrink-0 transition-all duration-700 ease-out delay-300 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
          }`}
      >
        <div>SYSTEM 2.0 • CONTROL PANEL</div>
        <div>SECURE DISCORD PROTOCOL</div>
      </footer>
    </div>
  );
}

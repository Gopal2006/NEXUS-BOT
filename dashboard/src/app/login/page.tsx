"use client";

import React, { Suspense, useEffect, useState } from "react";
import { signIn, useSession } from "next-auth/react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, ArrowRight, ShieldCheck, AlertCircle, Loader2 } from "lucide-react";
import { NexusLogo } from "@/components/NexusLogo";
import { BackgroundAurora } from "@/components/BackgroundAurora";
import { CustomCursor } from "@/components/CustomCursor";

function LoginContent() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const searchParams = useSearchParams();
  const errorParam = searchParams.get("error");
  const callbackUrl = searchParams.get("callbackUrl") || "/dashboard";
  const [isSigningIn, setIsSigningIn] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined" && window.location.hostname === "127.0.0.1") {
      window.location.hostname = "localhost";
    }
  }, []);

  useEffect(() => {
    if (status === "authenticated") {
      router.replace(callbackUrl);
    }
  }, [status, router, callbackUrl]);

  const getErrorMessage = (err: string | null) => {
    if (!err) return null;
    switch (err) {
      case "OAuthCallback":
        return "Authentication callback failed. Verify DISCORD_CLIENT_SECRET in .env.local and that your redirect URI matches http://localhost:3000/api/auth/callback/discord.";
      case "OAuthSignin":
      case "OAuthCreateAccount":
        return "Could not initialize session handoff with Discord.";
      case "Callback":
        return "Network or handshake error occurred during authorization callback.";
      case "AccessDenied":
        return "Access was declined by Discord.";
      default:
        return `Authorization failed (${err}).`;
    }
  };

  const errorMessage = getErrorMessage(errorParam);

  if (status === "loading" || status === "authenticated") {
    return (
      <div className="glass-strong rounded-2xl p-10 max-w-md w-full text-center space-y-4 shadow-2xl relative z-10">
        <Loader2 className="w-8 h-8 text-[var(--ice-silver)] animate-spin mx-auto" />
        <h2 className="text-base font-semibold tracking-wide text-[var(--ice-silver)]">
          AUTHENTICATING SESSION
        </h2>
        <p className="text-xs text-[var(--text-muted)] font-mono tracking-wider">
          Connecting to private dashboard...
        </p>
      </div>
    );
  }

  return (
    <div className="glass-strong rounded-2xl p-8 sm:p-10 max-w-md w-full text-center shadow-2xl relative overflow-hidden z-10">
      <div className="sheen" />

      {/* Geometric Logo */}
      <div className="w-12 h-12 rounded-2xl glass-soft border border-[var(--glass-border)] mx-auto flex items-center justify-center text-[var(--ice-silver)] mb-6 shadow-sm">
        <NexusLogo size={24} />
      </div>

      <div className="text-[10px] font-mono tracking-[0.25em] text-[var(--hint)] uppercase mb-2">
        NEXUS DASHBOARD
      </div>

      <h1 className="font-display font-bold text-2xl text-[var(--ice-silver)] tracking-tight mb-2">
        Sign in to NEXUS
      </h1>
      <p className="text-xs text-[var(--text-muted)] font-sans leading-relaxed mb-8">
        Authenticate with Discord to verify your server ownership and access the administrative console.
      </p>

      {errorMessage && (
        <div className="mb-6 p-4 rounded-xl glass-soft border border-[var(--error)]/30 text-left flex items-start gap-3">
          <AlertCircle className="w-4 h-4 text-[var(--error)] shrink-0 mt-0.5" />
          <div className="space-y-1">
            <div className="text-[10px] font-mono tracking-wider uppercase font-bold text-[var(--error)]">
              Authentication Notice
            </div>
            <div className="text-xs text-[var(--error)] leading-relaxed font-sans">{errorMessage}</div>
          </div>
        </div>
      )}

      <button
        onClick={() => {
          setIsSigningIn(true);
          signIn("discord", { callbackUrl });
        }}
        disabled={isSigningIn}
        className="w-full py-3.5 px-6 rounded-xl bg-[var(--ice-silver)] hover:opacity-90 text-[var(--ink)] font-mono text-xs font-bold tracking-[0.18em] uppercase transition-all duration-300 shadow-lg shadow-[var(--ice-silver)]/10 flex items-center justify-center gap-3 cursor-pointer group disabled:opacity-50"
      >
        {isSigningIn ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin text-[var(--ink)]" />
            <span>Redirecting to Discord...</span>
          </>
        ) : (
          <>
            <svg
              className="w-4 h-4 fill-current transition-transform duration-300 group-hover:scale-110"
              viewBox="0 0 24 24"
            >
              <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994.021-.041.001-.09-.041-.106a13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.929 1.793 8.18 1.793 12.061 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.893.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.028zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z" />
            </svg>
            <span>Continue with Discord</span>
            <ArrowRight className="w-3.5 h-3.5 transition-transform duration-300 group-hover:translate-x-1" />
          </>
        )}
      </button>

      {/* Security Notice */}
      <div className="mt-8 pt-6 border-t border-[var(--glass-border)] flex items-center justify-center gap-2 text-[11px] font-mono text-[var(--text-faint)]">
        <ShieldCheck className="w-3.5 h-3.5 text-[var(--success)]" />
        <span>End-to-end OAuth2 Guild Verification</span>
      </div>

      <div className="mt-4">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-xs text-[var(--text-muted)] hover:text-[var(--ice-silver)] transition-colors font-mono"
        >
          <ArrowLeft className="w-3 h-3" />
          <span>Back to system welcome</span>
        </Link>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <div className="min-h-screen bg-[var(--bg-deep)] text-[var(--ice-silver)] flex flex-col items-center justify-center p-4 relative overflow-hidden font-sans">
      <BackgroundAurora />
      <CustomCursor />
      <Suspense
        fallback={
          <div className="glass-strong rounded-2xl p-10 max-w-md w-full text-center space-y-4">
            <Loader2 className="w-8 h-8 text-[var(--ice-silver)] animate-spin mx-auto" />
            <h2 className="text-base font-semibold tracking-wide text-[var(--ice-silver)]">
              INITIALIZING
            </h2>
          </div>
        }
      >
        <LoginContent />
      </Suspense>
    </div>
  );
}

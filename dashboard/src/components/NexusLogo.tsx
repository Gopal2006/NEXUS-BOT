"use client";

import React from "react";

interface NexusLogoProps {
  className?: string;
  size?: number;
}

export function NexusLogo({ className = "w-6 h-6", size = 24 }: NexusLogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="NEXUS"
    >
      {/* Geometric N Node Network */}
      <line x1="5" y1="4" x2="5" y2="20" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="19" y1="4" x2="19" y2="20" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="5" y1="4" x2="19" y2="20" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
      <circle cx="5" cy="4" r="2" fill="currentColor" />
      <circle cx="19" cy="4" r="1.5" fill="currentColor" opacity="0.6" />
      <circle cx="5" cy="20" r="1.5" fill="currentColor" opacity="0.6" />
      <circle cx="19" cy="20" r="2" fill="currentColor" />
    </svg>
  );
}

export function NexusWordmark({ className = "" }: { className?: string }) {
  return (
    <div className={`flex items-center gap-2.5 ${className}`}>
      <div className="w-8 h-8 rounded-xl glass-soft border border-[var(--glass-border)] flex items-center justify-center text-[var(--ice-silver)] shadow-sm">
        <NexusLogo size={18} />
      </div>
      <span className="font-display font-bold tracking-[0.22em] text-sm text-[var(--ice-silver)] uppercase">
        NEXUS
      </span>
    </div>
  );
}

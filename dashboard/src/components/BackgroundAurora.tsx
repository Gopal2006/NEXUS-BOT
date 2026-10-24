"use client";

import React from "react";

export function BackgroundAurora() {
  return (
    <div
      aria-hidden="true"
      className="fixed inset-0 pointer-events-none z-0 overflow-hidden select-none bg-[var(--bg-deep)]"
    >
      {/* Film grain texture */}
      <div className="grain-overlay fixed inset-0 z-10 opacity-30" />

      {/* Subtle Monochrome Ambient Vignette (Clean Black & Grey, zero purple/aubergine) */}
      <div className="absolute -top-48 left-1/2 -translate-x-1/2 w-[900px] h-[500px] rounded-full bg-white/[0.02] blur-[160px]" />
      <div className="absolute top-1/2 -right-48 w-[600px] h-[600px] rounded-full bg-white/[0.012] blur-[180px]" />
      <div className="absolute -bottom-48 -left-24 w-[600px] h-[600px] rounded-full bg-white/[0.012] blur-[180px]" />
    </div>
  );
}

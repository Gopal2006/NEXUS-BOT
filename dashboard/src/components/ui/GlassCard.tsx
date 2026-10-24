"use client";

import React, { useRef } from "react";
import { cn } from "@/lib/utils";

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  variant?: "base" | "strong" | "soft";
  sheen?: boolean;
  spotlight?: boolean;
}

export function GlassCard({
  children,
  className = "",
  variant = "base",
  sheen = false,
  spotlight = true,
}: GlassCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!spotlight || !cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    cardRef.current.style.setProperty("--mouse-x", `${x}px`);
    cardRef.current.style.setProperty("--mouse-y", `${y}px`);
  };

  const variantClass =
    variant === "strong"
      ? "glass-strong"
      : variant === "soft"
      ? "glass-soft"
      : "glass";

  return (
    <div
      ref={cardRef}
      onMouseMove={handleMouseMove}
      className={cn(
        variantClass,
        sheen && "sheen",
        "relative p-6 transition-all duration-200 group overflow-hidden",
        className
      )}
    >
      {/* Soft Cursor Spotlight Glow (6-8% opacity) */}
      {spotlight && (
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 z-0"
          style={{
            background:
              "radial-gradient(400px circle at var(--mouse-x, 50%) var(--mouse-y, 50%), rgba(221, 227, 232, 0.07), transparent 70%)",
          }}
        />
      )}

      <div className="relative z-10">{children}</div>
    </div>
  );
}

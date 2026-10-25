import React from "react";
import { cn } from "@/lib/utils";

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  variant?: "base" | "strong" | "soft";
  sheen?: boolean;
  spotlight?: boolean;
}

export function GlassCard({ children, className = "", variant = "base", sheen = false }: GlassCardProps) {
  const surface = variant === "strong" ? "glass-strong" : variant === "soft" ? "glass-soft" : "glass";
  return (
    <section className={cn(surface, sheen && "sheen", "relative p-5 sm:p-6", className)}>
      {children}
    </section>
  );
}

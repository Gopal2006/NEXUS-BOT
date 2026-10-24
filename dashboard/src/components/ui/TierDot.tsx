import React from "react";
import { cn } from "@/lib/utils";

interface TierDotProps {
  tier: "public" | "staff" | "owner" | string;
  className?: string;
}

export function TierDot({ tier, className = "" }: TierDotProps) {
  const norm = tier.toLowerCase();

  let dotColor = "bg-[var(--text-faint)]";
  let label = "Public";

  if (norm === "owner" || norm === "server owner") {
    dotColor = "bg-[var(--warning)] shadow-[0_0_6px_rgba(251,191,36,0.5)]";
    label = "Owner";
  } else if (norm === "staff") {
    dotColor = "bg-[var(--ice-silver)] shadow-[0_0_6px_rgba(221,227,232,0.5)]";
    label = "Staff";
  } else {
    dotColor = "bg-[var(--text-faint)]";
    label = "Public";
  }

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 text-xs font-mono text-[var(--text-muted)] select-none",
        className
      )}
    >
      <span className={cn("w-1.5 h-1.5 rounded-full shrink-0", dotColor)} />
      <span>{label}</span>
    </span>
  );
}

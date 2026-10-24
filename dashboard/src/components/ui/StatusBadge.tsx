import React from "react";
import { cn } from "@/lib/utils";

export type StatusVariant = "active" | "off" | "warning" | "error" | "info";

interface StatusBadgeProps {
  status: StatusVariant | string;
  label?: string;
  className?: string;
}

export function StatusBadge({ status, label, className = "" }: StatusBadgeProps) {
  const norm = status.toLowerCase();

  let text = label;
  let bgClass = "bg-[var(--tint)] text-[var(--text-muted)] border-[var(--glass-border)]";
  let dotClass = "bg-[var(--text-faint)]";

  if (norm === "active" || norm === "enabled" || norm === "success" || norm === "online") {
    text = text || "Active";
    bgClass = "bg-[var(--success)]/10 text-[var(--success)] border-[var(--success)]/25";
    dotClass = "bg-[var(--success)] shadow-[0_0_6px_rgba(52,211,153,0.6)]";
  } else if (norm === "warning" || norm === "needs setup" || norm === "incomplete" || norm === "checking") {
    text = text || "Needs setup";
    bgClass = "bg-[var(--warning)]/10 text-[var(--warning)] border-[var(--warning)]/25";
    dotClass = "bg-[var(--warning)] animate-pulse";
  } else if (norm === "error" || norm === "failed" || norm === "offline") {
    text = text || "Error";
    bgClass = "bg-[var(--error)]/10 text-[var(--error)] border-[var(--error)]/25";
    dotClass = "bg-[var(--error)]";
  } else {
    text = text || "Off";
    bgClass = "bg-[var(--tint)] text-[var(--text-muted)] border-[var(--glass-border)]";
    dotClass = "bg-[var(--text-faint)]";
  }

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-mono tracking-wider uppercase border select-none",
        bgClass,
        className
      )}
    >
      <span className={cn("w-1.5 h-1.5 rounded-full shrink-0", dotClass)} />
      <span>{text}</span>
    </span>
  );
}

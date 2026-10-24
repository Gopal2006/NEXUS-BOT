import React from "react";
import { cn } from "@/lib/utils";

interface IconTileProps {
  icon: React.ReactNode;
  className?: string;
  size?: "sm" | "md" | "lg";
}

export function IconTile({ icon, className = "", size = "md" }: IconTileProps) {
  const sizeClasses =
    size === "sm"
      ? "w-8 h-8 rounded-lg text-sm"
      : size === "lg"
      ? "w-14 h-14 rounded-2xl text-xl"
      : "w-11 h-11 rounded-xl text-base";

  return (
    <div
      className={cn(
        "glass-soft flex items-center justify-center text-[var(--ice-silver)] shrink-0 shadow-sm border border-[var(--glass-border)] transition-transform duration-200 group-hover:scale-105",
        sizeClasses,
        className
      )}
    >
      {icon}
    </div>
  );
}

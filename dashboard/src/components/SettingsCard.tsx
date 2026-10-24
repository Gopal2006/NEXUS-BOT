import React from "react";
import { cn } from "@/lib/utils";

interface SettingsCardProps {
  title: string;
  description?: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
}

export function SettingsCard({
  title,
  description,
  icon,
  children,
  footer,
  className,
}: SettingsCardProps) {
  return (
    <div
      className={cn(
        "glass rounded-2xl p-6 mb-6 transition-all duration-300 hover:border-[var(--ice-silver)]/25",
        className
      )}
    >
      <div className="flex items-start gap-4 mb-5">
        {icon && (
          <div className="p-2.5 glass-soft border border-[var(--glass-border)] rounded-xl text-[var(--ice-silver)] shrink-0 mt-0.5">
            {icon}
          </div>
        )}
        <div>
          <h3 className="font-display font-bold text-base text-[var(--ice-silver)] tracking-tight">
            {title}
          </h3>
          {description && (
            <p className="text-xs text-[var(--text-muted)] mt-1 leading-relaxed">
              {description}
            </p>
          )}
        </div>
      </div>

      <div className="space-y-4">{children}</div>

      {footer && (
        <div className="mt-6 pt-4 border-t border-[var(--glass-border)] flex items-center justify-between text-xs text-[var(--text-muted)] font-mono">
          {footer}
        </div>
      )}
    </div>
  );
}

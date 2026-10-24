import React from "react";

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className = "",
}: EmptyStateProps) {
  return (
    <div
      className={`text-center py-12 px-6 rounded-xl border border-[var(--border)] bg-[var(--surface)]/40 max-w-lg mx-auto ${className}`}
    >
      {icon && (
        <div className="w-10 h-10 rounded-xl bg-[var(--card)] border border-[var(--border)] mx-auto flex items-center justify-center text-[var(--text-muted)] mb-3">
          {icon}
        </div>
      )}
      <h3 className="text-base font-semibold text-[var(--text)] mb-1">
        {title}
      </h3>
      <p className="text-[13px] text-[var(--text-muted)] max-w-sm mx-auto mb-5 leading-relaxed">
        {description}
      </p>
      {action && <div>{action}</div>}
    </div>
  );
}

import React from "react";

interface PageHeaderProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export function PageHeader({ icon, title, description, action }: PageHeaderProps) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-[var(--border)]">
      <div className="flex items-start sm:items-center gap-3.5">
        {icon && (
          <div className="w-10 h-10 rounded-xl bg-[var(--surface)] border border-[var(--border)] flex items-center justify-center text-[var(--text)] shrink-0 shadow-sm">
            {icon}
          </div>
        )}
        <div>
          <h1 className="font-display text-4xl sm:text-5xl font-semibold tracking-tight text-[var(--text)] leading-[.94]">
            {title}
          </h1>
          {description && (
            <p className="text-sm text-[var(--text-muted)] mt-0.5 leading-normal">
              {description}
            </p>
          )}
        </div>
      </div>
      {action && <div className="shrink-0 flex items-center gap-3">{action}</div>}
    </div>
  );
}

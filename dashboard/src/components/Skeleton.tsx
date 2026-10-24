import React from "react";
import { cn } from "@/lib/utils";

export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-dark-subtle/80", className)}
      {...props}
    />
  );
}

export function CardSkeleton() {
  return (
    <div className="bg-dark-card border border-dark-border rounded-xl p-5 mb-5 space-y-4">
      <div className="flex items-center gap-3">
        <Skeleton className="w-10 h-10 rounded-lg" />
        <div className="space-y-2">
          <Skeleton className="w-36 h-4" />
          <Skeleton className="w-64 h-3" />
        </div>
      </div>
      <Skeleton className="w-full h-10 rounded-lg" />
    </div>
  );
}

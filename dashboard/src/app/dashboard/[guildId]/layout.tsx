"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { FloatingSidebar } from "@/components/FloatingSidebar";
import { FloatingTopBar } from "@/components/FloatingTopBar";

export default function GuildDashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const params = useParams();
  const guildId = params.guildId as string;
  const [guild, setGuild] = useState<{ name: string; icon: string | null } | null>(null);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  useEffect(() => {
    async function loadGuild() {
      try {
        const res = await fetch(`/api/backend/guilds/${guildId}`);
        if (res.ok) {
          const data = await res.json();
          setGuild(data);
        }
      } catch {
        // Fallback handled
      }
    }
    if (guildId) {
      loadGuild();
    }
  }, [guildId]);

  return (
    <div className="min-h-screen bg-[var(--bg-deep)] text-[var(--ice-silver)] relative overflow-x-hidden selection:bg-[var(--accent)]/30">
       <div className="relative z-10 flex min-h-screen">
        {/* Floating Sidebar (Desktop: floating panel with 16px margins, Mobile: glass drawer) */}
        <FloatingSidebar
          guildId={guildId}
          isMobileOpen={mobileSidebarOpen}
          onCloseMobile={() => setMobileSidebarOpen(false)}
        />

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col min-w-0 pb-12">
          {/* Floating Top Bar (16px from top) */}
          <FloatingTopBar
            guildName={guild?.name}
            guildIcon={guild?.icon}
            onToggleMobileSidebar={() => setMobileSidebarOpen((prev) => !prev)}
          />

          {/* Centered Page Content Container (max-width 1240px, generous whitespace) */}
          <main className="flex-1 px-4 sm:px-7 lg:px-10 max-w-[1360px] w-full mx-auto">
            {children}
          </main>
        </div>
      </div>
    </div>
  );
}

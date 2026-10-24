import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/components/Providers";
import { CustomCursor } from "@/components/CustomCursor";

export const metadata: Metadata = {
  title: "NEXUS",
  description: "Discord bot management interface for NEXUS.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className="bg-[var(--bg-deep)] text-[var(--ice-silver)] min-h-screen relative antialiased selection:bg-[var(--ice-silver)]/20 selection:text-white" suppressHydrationWarning>
        <CustomCursor />
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

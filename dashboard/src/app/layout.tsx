import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/components/Providers";
export const metadata: Metadata = { title: { default: "Nexus — Community operations", template: "%s · Nexus" }, description: "A clear workspace for managing your Discord community." };
export default function RootLayout({ children }: { children: React.ReactNode }) {
 return <html lang="en"><body className="min-h-screen antialiased"><Providers>{children}</Providers></body></html>;
}

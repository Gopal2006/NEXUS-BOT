import { withAuth } from "next-auth/middleware";
import { NextResponse } from "next/server";

export default withAuth(
  function middleware(req) {
    const token = req.nextauth.token;
    const pathname = req.nextUrl.pathname;

    // Protect /admin: require user ID to be in NEXT_PUBLIC_ADMIN_IDS
    if (pathname.startsWith("/admin")) {
      const adminIds = (process.env.NEXT_PUBLIC_ADMIN_IDS || "")
        .split(",")
        .map((id) => id.trim());
      const userId = token?.sub;
      if (!userId || !adminIds.includes(userId)) {
        return NextResponse.redirect(new URL("/dashboard", req.url));
      }
    }

    return NextResponse.next();
  },
  {
    callbacks: {
      authorized: ({ token }) => !!token,
    },
    pages: {
      signIn: "/login",
    },
    secret: process.env.NEXTAUTH_SECRET || "local_dev_secret_fallback_key_32_characters",
  }
);

export const config = {
  matcher: ["/dashboard/:path*", "/admin/:path*"],
};

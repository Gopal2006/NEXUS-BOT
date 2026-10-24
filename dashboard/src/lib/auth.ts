import { NextAuthOptions } from "next-auth";
import DiscordProvider from "next-auth/providers/discord";

const rawClientId = (process.env.DISCORD_CLIENT_ID || "").trim();
let clientSecret = (process.env.DISCORD_CLIENT_SECRET || "").trim();

// Auto-sanitize: if client ID was accidentally appended to secret, strip it
if (rawClientId && clientSecret.endsWith(rawClientId) && clientSecret.length > 32) {
  clientSecret = clientSecret.slice(0, -rawClientId.length).trim();
}

export const authOptions: NextAuthOptions = {
  providers: [
    DiscordProvider({
      clientId: rawClientId,
      clientSecret: clientSecret,
      authorization: { params: { scope: "identify guilds" } },
      issuer: "https://discord.com",
      checks: ["none"],
    }),
  ],
  useSecureCookies: false,
  callbacks: {
    async session({ session, token }) {
      if (session.user && token.sub) {
        (session.user as any).id = token.sub;
      }
      return session;
    },
    async jwt({ token, user, account }) {
      if (user) {
        token.sub = user.id;
      }
      if (account) {
        token.accessToken = account.access_token;
      }
      return token;
    },
  },
  pages: {
    signIn: "/login",
  },
  debug: true,
  logger: {
    error(code, metadata) {
      console.error(`[NextAuth Error] [${code}]:`, metadata);
    },
    warn(code) {
      console.warn(`[NextAuth Warn] [${code}]`);
    },
    debug(code, metadata) {
      console.log(`[NextAuth Debug] [${code}]:`, metadata);
    },
  },
  secret: process.env.NEXTAUTH_SECRET || "local_dev_secret_fallback_key_32_characters",
};

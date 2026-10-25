export const SITE_URL = "https://nexusdc.vercel.app";
export const SITE_NAME = "NEXUS";
export const INVITE_URL = "https://discord.com/api/oauth2/authorize?client_id=1560655249276936192&permissions=1374792445014&scope=bot%20applications.commands";
export const SUPPORT_URL = "TODO_SUPPORT_URL";
export const GITHUB_URL = "https://github.com/adityabugalia063/NEXUS-BOT";
export const CONTACT_EMAIL = "TODO_CONTACT_EMAIL";
export const DASHBOARD_URL = "https://nexusdc.vercel.app/dashboard";

export const isTodo = (value: string) => value.startsWith("TODO_");
export const safeHref = (value: string, fallback: string) =>
  isTodo(value) ? fallback : value;

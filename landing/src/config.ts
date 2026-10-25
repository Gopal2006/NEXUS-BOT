export const SITE_URL = "https://nexus-bot.example";
export const SITE_NAME = "NEXUS";
export const INVITE_URL = "TODO_INVITE_URL";
export const SUPPORT_URL = "TODO_SUPPORT_URL";
export const GITHUB_URL = "TODO_GITHUB_URL";
export const CONTACT_EMAIL = "TODO_CONTACT_EMAIL";
export const DASHBOARD_URL = "TODO_DASHBOARD_URL";

export const isTodo = (value: string) => value.startsWith("TODO_");
export const safeHref = (value: string, fallback: string) =>
  isTodo(value) ? fallback : value;

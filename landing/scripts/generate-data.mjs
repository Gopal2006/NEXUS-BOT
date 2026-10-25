import fs from "node:fs";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "..");
const audit = fs.readFileSync(path.resolve(root, "../FEATURES.md"), "utf8");
const tick = String.fromCharCode(96);

const featureSection = audit.split("## Landing feature areas")[1]?.split("## Gaps / needs human input")[0] || "";
const featureRows = featureSection.split(/\r?\n/).filter((line) => line.startsWith("|") && !line.includes("|---") && !line.includes("| Feature area |"))
  .map((line) => line.split("|").slice(1, -1).map((cell) => cell.trim().replace(/^`|`$/g, "")));
if (!featureRows.length) throw new Error("FEATURES.md is missing its Landing feature areas table.");
const requiredPhrases = ["Moderation", "Tickets", "Leveling", "Giveaways", "Autorole", "Audit logging", "Announcements and direct messages", "Autoresponder", "Games"];
for (const phrase of requiredPhrases) {
  if (!audit.toLowerCase().includes(phrase.toLowerCase())) throw new Error("FEATURES.md is missing verified feature phrase: " + phrase);
}

const categoryAliases = {
  "Admin and setup": "Setup",
  "Moderation and channel control": "Moderation",
  "Member management": "Member management",
  "Engagement and social": "Engagement",
  "Games": "Games",
  "Giveaways": "Giveaways",
  "Polls": "Polls",
  "Tickets": "Tickets",
  "Announcements and direct messages": "Communication",
  "Utility": "Utility",
  "Global bot-owner prefix commands": "Internal",
};
const argsKnown = ["activity_type", "activity_text", "message_id", "delete_days", "user_id", "match_type", "thumbnail", "opponent", "nickname", "trigger", "response", "winners", "seconds", "member", "reason", "duration", "channel", "message", "status", "role", "scope", "amount", "page", "user", "action", "level", "title", "description", "color", "embed", "ping", "image", "target", "mode", "category"];
const examples = {
  member: "@member", opponent: "@member", user: "@member", target: "@member",
  role: "@Staff", channel: "#channel", message: '"Example message"',
  reason: '"Example reason"', duration: "10m", delete_days: "1", user_id: "USER_ID",
  message_id: "MESSAGE_ID", amount: "5", seconds: "10", page: "1", status: "enabled",
  action: "add", level: "5", scope: "all", mode: "guild", category: "overview",
  trigger: "hello", response: '"Hello there"', match_type: "exact", winners: "1",
  title: '"Support"', description: '"Open a ticket"', color: "#5865F2",
  ping: "false", image: "IMAGE_URL", thumbnail: "THUMBNAIL_URL", embed: "true",
  activity_type: "playing", activity_text: '"community"',
};
const stripTicks = (text) => text.split(tick).join("").trim();
function codeTokens(cell) {
  const expression = new RegExp(tick + "([^" + tick + "]+)" + tick, "g");
  return [...cell.matchAll(expression)].map((match) => match[1].trim()).filter(Boolean);
}
function getArguments(cell) {
  const normalized = stripTicks(cell).toLowerCase();
  return argsKnown.filter((name) => new RegExp("(^|[^a-z0-9_])" + name + "([^a-z0-9_]|$)").test(normalized));
}
function exampleFor(command, args) {
  return [command, ...args.map((name) => name + ":" + (examples[name] || "<" + name + ">"))].join(" ");
}

const commands = [];
let category = "";
let inCommands = false;
for (const line of audit.split(/\r?\n/)) {
  if (line.startsWith("## 2. Commands")) { inCommands = true; continue; }
  if (line.startsWith("### Hero commands")) { inCommands = false; continue; }
  if (!inCommands) continue;
  if (line.startsWith("### ")) {
    const rawHeading = line.slice(4).split(" — ")[0].trim();
    category = categoryAliases[rawHeading] || rawHeading;
    continue;
  }
  if (!line.startsWith("|") || line.includes("|---") || line.includes("| Command |")) continue;
  const cells = line.split("|").slice(1, -1).map((cell) => cell.trim());
  if (cells.length !== 4 || !category) continue;
  const spellings = [...new Set(codeTokens(cells[0]))].filter((value) => value.startsWith("/") || value.startsWith("n!") || /^[a-z][a-z0-9_-]*$/i.test(value));
  if (!spellings.length) continue;
  const args = getArguments(cells[1]);
  const tierText = stripTicks(cells[2]).toLowerCase();
  let tier = "Public";
  if (tierText.includes("bot_owner") || category === "Internal") tier = "Bot owner";
  else if (tierText.includes("staff") && tierText.includes("owner")) tier = "Staff / owner";
  else if (tierText.includes("staff")) tier = "Staff";
  else if (tierText.includes("owner")) tier = "Owner";
  const primary = spellings.find((value) => value.startsWith("/")) || spellings[0];
  commands.push({
    id: category.toLowerCase().replace(/[^a-z0-9]+/g, "-") + "-" + String(commands.length + 1),
    category,
    name: primary,
    command: primary,
    spellings,
    slash: spellings.filter((value) => value.startsWith("/")),
    prefix: spellings.filter((value) => value.startsWith("n!")),
    aliases: spellings.filter((value) => !value.startsWith("/") && !value.startsWith("n!")),
    arguments: args,
    argumentNotes: stripTicks(cells[1]),
    tier,
    description: stripTicks(cells[3]),
    example: exampleFor(primary, args),
    visibility: tier === "Bot owner" ? "internal" : "public-reference",
  });
}
if (!commands.length) throw new Error("No command rows were parsed from FEATURES.md.");

const logCountWord = audit.match(/creates a private NEXUS LOGS category and (\w+) log channels/i)?.[1]?.toLowerCase();
const countWords = { one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10 };
const logChannelCount = countWords[logCountWord];
const invitationPermissionInteger = Number(audit.match(/permission integer \*\*(\d+)\*\*/i)?.[1]);
const commandTextMaxCharacters = Number(audit.match(/truncated to (\d+) characters/i)?.[1]);
if (!logChannelCount || !invitationPermissionInteger || !commandTextMaxCharacters) {
  throw new Error("FEATURES.md is missing a numeric fact used in the landing copy.");
}
const write = (name, data) => fs.writeFileSync(path.resolve(root, "src/data", name), JSON.stringify(data, null, 2) + "\n");
write("commands.json", { source: "FEATURES.md", generatedAtBuild: true, commands });
write("features.json", { source: "FEATURES.md", generatedAtBuild: true, features: featureRows.map(([name, description, command, icon]) => ({ name, description, command, icon })), verifiedFacts: { logChannelCount, invitationPermissionInteger, commandTextMaxCharacters } });
console.log("Generated " + commands.length + " command entries and " + featureRows.length + " feature areas from FEATURES.md.");

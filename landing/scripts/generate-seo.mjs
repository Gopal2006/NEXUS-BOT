import fs from "node:fs";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "..");
const config = fs.readFileSync(path.resolve(root, "src/config.ts"), "utf8");
const match = config.match(/SITE_URL\s*=\s*"([^"]+)"/);
if (!match) throw new Error("SITE_URL is missing from src/config.ts");
const site = match[1].replace(/\/+$/, "");
const pages = ["/", "/commands/", "/privacy/", "/terms/"];
const xml = [
  '<?xml version="1.0" encoding="UTF-8"?>',
  '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
  ...pages.map((page) => "  <url><loc>" + site + page + "</loc></url>"),
  "</urlset>",
].join("\n") + "\n";
fs.writeFileSync(path.resolve(root, "public/sitemap.xml"), xml);
fs.writeFileSync(path.resolve(root, "public/robots.txt"), "User-agent: *\nAllow: /\nSitemap: " + site + "/sitemap.xml\n");
console.log("Generated sitemap.xml and robots.txt for " + site);

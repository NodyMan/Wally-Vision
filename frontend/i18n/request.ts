import fs from "node:fs";
import path from "node:path";
import { hasLocale } from "next-intl";
import { getRequestConfig } from "next-intl/server";
import { routing } from "./routing";

const CORE_NAMESPACES = [
  "common",
  "home",
  "onboarding",
  "about",
  "findings",
  "errors",
  "presets",
] as const;

export default getRequestConfig(async ({ requestLocale }) => {
  const requested = await requestLocale;
  const locale = hasLocale(routing.locales, requested)
    ? requested
    : routing.defaultLocale;

  const messages: Record<string, unknown> = {};

  for (const ns of CORE_NAMESPACES) {
    messages[ns] = (await import(`../messages/${locale}/${ns}.json`)).default;
  }

  // Merge any additional namespace files added by teammates (#1 viewer, #2 science/features)
  const localeDir = path.join(process.cwd(), "messages", locale);
  if (fs.existsSync(localeDir)) {
    for (const file of fs.readdirSync(localeDir)) {
      if (!file.endsWith(".json")) continue;
      const ns = file.slice(0, -5);
      if (ns in messages) continue;
      try {
        messages[ns] = JSON.parse(
          fs.readFileSync(path.join(localeDir, file), "utf8")
        );
      } catch {
        // Ignore malformed optional namespace file during early development
      }
    }
  }

  return {
    locale,
    messages,
  };
});

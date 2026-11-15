import fs from "node:fs";
import path from "node:path";

const LOCALES = ["en", "ru", "uz"];
const BASE_LOCALE = "en";
const MESSAGES_DIR = path.resolve(process.cwd(), "frontend", "messages");

function flattenEntries(obj, prefix = "", out = new Map()) {
  for (const [key, value] of Object.entries(obj)) {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    if (value !== null && typeof value === "object" && !Array.isArray(value)) {
      flattenEntries(value, fullKey, out);
    } else {
      out.set(fullKey, value);
    }
  }
  return out;
}

function extractPlaceholders(value) {
  if (typeof value !== "string") return [];
  const matches = value.match(/\{[a-zA-Z0-9_]+\}/g) || [];
  return [...new Set(matches)].sort();
}

if (!fs.existsSync(MESSAGES_DIR)) {
  console.error(`Messages directory not found: ${MESSAGES_DIR}`);
  process.exit(1);
}

const baseDir = path.join(MESSAGES_DIR, BASE_LOCALE);
if (!fs.existsSync(baseDir)) {
  console.error(`Base locale directory not found: ${baseDir}`);
  process.exit(1);
}

const namespaceFiles = fs
  .readdirSync(baseDir)
  .filter((file) => file.endsWith(".json"))
  .sort();

let hasErrors = false;

for (const nsFile of namespaceFiles) {
  const basePath = path.join(baseDir, nsFile);
  const baseJson = JSON.parse(fs.readFileSync(basePath, "utf8"));
  const baseEntries = flattenEntries(baseJson);

  for (const [key, val] of baseEntries) {
    if (typeof val === "string" && val.trim().length === 0) {
      console.error(`[EMPTY STRING] ${BASE_LOCALE}/${nsFile}: "${key}"`);
      hasErrors = true;
    }
  }

  for (const locale of LOCALES) {
    if (locale === BASE_LOCALE) continue;
    const targetPath = path.join(MESSAGES_DIR, locale, nsFile);
    if (!fs.existsSync(targetPath)) {
      console.error(`[MISSING FILE] ${locale}/${nsFile}`);
      hasErrors = true;
      continue;
    }

    const targetJson = JSON.parse(fs.readFileSync(targetPath, "utf8"));
    const targetEntries = flattenEntries(targetJson);

    for (const [key, baseVal] of baseEntries) {
      if (!targetEntries.has(key)) {
        console.error(`[MISSING KEY] ${locale}/${nsFile}: "${key}"`);
        hasErrors = true;
        continue;
      }
      const targetVal = targetEntries.get(key);
      if (typeof targetVal === "string" && targetVal.trim().length === 0) {
        console.error(`[EMPTY STRING] ${locale}/${nsFile}: "${key}"`);
        hasErrors = true;
      }
      const basePh = extractPlaceholders(baseVal).join(",");
      const targetPh = extractPlaceholders(targetVal).join(",");
      if (basePh !== targetPh) {
        console.error(
          `[PLACEHOLDER MISMATCH] ${locale}/${nsFile}: "${key}" (expected [${basePh}], got [${targetPh}])`
        );
        hasErrors = true;
      }
    }

    for (const key of targetEntries.keys()) {
      if (!baseEntries.has(key)) {
        console.error(`[EXTRA KEY] ${locale}/${nsFile}: "${key}"`);
        hasErrors = true;
      }
    }
  }
}

// Also warn/fail on extra namespace files present in non-base locales but missing in base
for (const locale of LOCALES) {
  if (locale === BASE_LOCALE) continue;
  const localeDir = path.join(MESSAGES_DIR, locale);
  if (!fs.existsSync(localeDir)) continue;
  for (const file of fs.readdirSync(localeDir).filter((f) => f.endsWith(".json"))) {
    if (!namespaceFiles.includes(file)) {
      console.error(`[MISSING BASE FILE] ${BASE_LOCALE}/${file} (present in ${locale})`);
      hasErrors = true;
    }
  }
}

if (hasErrors) {
  console.error("i18n check failed.");
  process.exit(1);
}

// Verify shared/presets.json stays synchronized with frontend/lib/mocks/presets.json
const sharedPresetsPath = path.resolve(process.cwd(), "shared", "presets.json");
const frontendPresetsPath = path.resolve(
  process.cwd(),
  "frontend",
  "lib",
  "mocks",
  "presets.json"
);
if (fs.existsSync(sharedPresetsPath) && fs.existsSync(frontendPresetsPath)) {
  const sharedRaw = JSON.stringify(
    JSON.parse(fs.readFileSync(sharedPresetsPath, "utf8"))
  );
  const frontendRaw = JSON.stringify(
    JSON.parse(fs.readFileSync(frontendPresetsPath, "utf8"))
  );
  if (sharedRaw !== frontendRaw) {
    console.error(
      "[PRESETS DRIFT] shared/presets.json and frontend/lib/mocks/presets.json differ!"
    );
    process.exit(1);
  }
}

console.log(
  `i18n check passed (${namespaceFiles.length} namespace(s) verified across ${LOCALES.join(", ")}).`
);

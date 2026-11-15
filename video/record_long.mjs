// Screen recording of the running SkyBlink app for the long demo video (real app, real SPHEREx data).
// Takes: H search + Barnard, I sky map, J RW Aur saturated light curve, K Simple mode + trainer, L report + findings, M phone.
// Headless Chrome screencast frames + logged cursor and marks; video/build_video_long.py cuts them to the voice.
// Usage: cd C:\skyblink_video && node record_long.mjs   (needs playwright-core there, app on :3010)
// Developed with SI assistance (Claude); reviewed by team #1.
import { chromium } from "playwright-core";
import fs from "node:fs";
import path from "node:path";

const BASE = process.env.SKYBLINK_URL || "http://localhost:3010";
const OUT = process.env.REC_DIR || "C:\\skyblink_video\\long\\rec";
const EPS = "ra=331.04383&dec=-56.78269&fov=300&det=6&name=Epsilon%20Indi%20B";
const BARNARD = "ra=269.452083&dec=4.693364&fov=300&mode=diff&det=2&name=Barnard%27s%20Star";
const RWAUR = "ra=76.95642&dec=30.40141&fov=300&mode=frames&det=2&name=RW%20Aurigae";
const WANT = (process.env.TAKES || "H,I,J,K,L,M").split(",");
for (const t of WANT) fs.rmSync(path.join(OUT, t), { recursive: true, force: true });

const browser = await chromium.launch({ channel: "chrome", headless: true, args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] });
const context = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
await context.addInitScript(() => { try { localStorage.setItem("skyblink_onboarding_done", "1"); } catch {} });
const page = await context.newPage();
for (const p of ["/en", "/en/about", "/en/findings", `/en/view?${BARNARD}`, `/en/view?${RWAUR}`, `/en/view?${EPS}&mode=diff`]) {
  await page.goto(BASE + p, { waitUntil: "networkidle", timeout: 120000 });
}

async function take(name, setupUrl, script) {
  if (!WANT.includes(name)) return;
  const dir = path.join(OUT, name);
  fs.mkdirSync(path.join(dir, "frames"), { recursive: true });
  await page.goto(BASE + setupUrl, { waitUntil: "networkidle", timeout: 120000 });
  await page.waitForTimeout(1500);
  const cdp = await context.newCDPSession(page);
  const frames = [], marks = {}, mouse = [];
  const wall0 = Date.now();
  const now = () => (Date.now() - wall0) / 1000;
  cdp.on("Page.screencastFrame", async (f) => {
    const fn = `f${String(frames.length).padStart(5, "0")}.jpg`;
    fs.writeFileSync(path.join(dir, "frames", fn), Buffer.from(f.data, "base64"));
    frames.push({ t: now(), name: fn });
    try { await cdp.send("Page.screencastFrameAck", { sessionId: f.sessionId }); } catch {}
  });
  await cdp.send("Page.startScreencast", { format: "jpeg", quality: 92, maxWidth: 1920, maxHeight: 1080, everyNthFrame: 1 });
  let mx = 1300, my = 820;
  const a = {
    mark: (k) => { marks[k] = now(); console.log(name, k, marks[k].toFixed(2)); },
    idle: async (ms) => { const end = Date.now() + ms; while (Date.now() < end) { mouse.push({ t: now(), x: mx, y: my }); await page.waitForTimeout(40); } },
    moveTo: async (x, y, ms = 700) => {
      const steps = Math.max(8, Math.round(ms / 16)), sx = mx, sy = my;
      for (let i = 1; i <= steps; i++) {
        const e = i / steps, k = e * e * (3 - 2 * e);
        mx = sx + (x - sx) * k; my = sy + (y - sy) * k;
        await page.mouse.move(mx, my); mouse.push({ t: now(), x: mx, y: my });
        await page.waitForTimeout(ms / steps);
      }
    },
    click: async () => { mouse.push({ t: now(), x: mx, y: my, click: true }); await page.mouse.down(); await page.mouse.up(); },
  };
  a.hoverEl = async (loc, ms = 700) => { const b = await loc.boundingBox(); await a.moveTo(b.x + b.width / 2, b.y + b.height / 2, ms); };
  a.clickEl = async (loc, ms = 700) => { await a.hoverEl(loc, ms); await a.click(); };
  await a.idle(300);
  await script(a);
  await cdp.send("Page.stopScreencast");
  await page.waitForTimeout(300);
  fs.writeFileSync(path.join(dir, "log.json"), JSON.stringify({ frames, marks, mouse }, null, 1));
  console.log(name, "frames", frames.length, "last", frames.at(-1)?.t.toFixed(2));
}

await take("H", "/en", async (a) => {
  a.mark("start");
  await a.idle(600);
  await a.clickEl(page.locator("form input").first(), 700);
  await page.keyboard.type("Barnard's Star", { delay: 85 });
  a.mark("typed");
  await a.idle(500);
  await a.hoverEl(page.getByRole("heading", { name: "Barnard's Star" }).first(), 800);
  a.mark("click");
  await a.click();
  await page.waitForURL(/\/view/, { timeout: 60000 });
  await page.getByRole("button", { name: "Difference", exact: true }).first().waitFor({ timeout: 60000 });
  await page.waitForTimeout(600);
  a.mark("viewer");
  for (let i = 0; i < 2; i++) { await page.keyboard.press("+"); await a.idle(220); }
  await a.moveTo(1320, 760, 600);
  await a.idle(5000);
  a.mark("end");
});

await take("I", `/en/view?${EPS}&mode=diff`, async (a) => {
  await page.evaluate(() => window.scrollTo(0, 420));
  await page.waitForTimeout(400);
  const tab = page.getByRole("tab", { name: "Sky map" }).or(page.getByRole("button", { name: "Sky map", exact: true })).first();
  a.mark("start");
  await a.clickEl(tab, 600);
  await a.idle(400);
  const load = page.getByRole("button", { name: /Load the sky map/ }).first();
  if (await load.count()) { await a.clickEl(load, 500); }
  a.mark("loading");
  for (let i = 0; i < 8; i++) { await page.mouse.wheel(0, 60); await a.idle(40); }
  await a.idle(14000);
  a.mark("end");
});

await take("J", `/en/view?${RWAUR}`, async (a) => {
  await page.evaluate(() => window.scrollTo(0, 420));
  await page.waitForTimeout(400);
  const tab = page.getByRole("tab", { name: "Light curve" }).or(page.getByRole("button", { name: "Light curve", exact: true })).first();
  a.mark("start");
  await a.clickEl(tab, 600);
  await a.idle(250);
  await a.clickEl(page.getByRole("button", { name: /Measure brightness over time/ }).first(), 500);
  a.mark("built");
  for (let i = 0; i < 8; i++) { await page.mouse.wheel(0, 60); await a.idle(40); }
  await a.idle(4000);
  a.mark("end");
});

await take("K", `/en/view?${EPS}&mode=diff`, async (a) => {
  const simple = page.locator("button[aria-pressed]").filter({ hasText: /Expert|Simple/ }).first();
  a.mark("start");
  await a.clickEl(simple, 700);
  await a.idle(1800);
  a.mark("about");
  await page.goto(BASE + "/en/about", { waitUntil: "networkidle" });
  await page.waitForTimeout(500);
  const play = page.getByRole("button", { name: /^Play/ }).first();
  await play.scrollIntoViewIfNeeded();
  await page.evaluate(() => window.scrollBy(0, 200));
  await a.idle(500);
  a.mark("trainer");
  await a.clickEl(play, 700);
  await a.idle(4500);
  a.mark("end");
});

await take("L", `/en/view?${EPS}&mode=diff`, async (a) => {
  const btn = page.getByRole("button", { name: /I found something/ }).first();
  a.mark("start");
  await a.clickEl(btn, 700);
  await a.idle(500);
  const note = page.locator("textarea").first();
  await a.clickEl(note, 500);
  await page.keyboard.type("Demo entry: black/white pair at the brown dwarf, matches the catalogue motion. Candidate to check.", { delay: 18 });
  await a.idle(300);
  a.mark("submit");
  await a.clickEl(page.locator('[role="dialog"] button[type="submit"]').first().or(page.getByRole("button", { name: /Submit|Send/ }).last()), 600);
  await a.idle(1500);
  a.mark("feed");
  await page.goto(BASE + "/en/findings", { waitUntil: "networkidle" });
  await a.idle(3500);
  a.mark("end");
});

if (WANT.includes("M")) {
  const dir = path.join(OUT, "M");
  fs.mkdirSync(path.join(dir, "frames"), { recursive: true });
  const pctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  await pctx.addInitScript(() => { try { localStorage.setItem("skyblink_onboarding_done", "1"); } catch {} });
  const pp = await pctx.newPage();
  await pp.goto(BASE + `/ru/view?${EPS}&mode=diff`, { waitUntil: "networkidle", timeout: 120000 });
  await pp.waitForTimeout(1500);
  const cdp = await pctx.newCDPSession(pp);
  const frames = [];
  const wall0 = Date.now();
  const now = () => (Date.now() - wall0) / 1000;
  cdp.on("Page.screencastFrame", async (f) => {
    const fn = `f${String(frames.length).padStart(5, "0")}.jpg`;
    fs.writeFileSync(path.join(dir, "frames", fn), Buffer.from(f.data, "base64"));
    frames.push({ t: now(), name: fn });
    try { await cdp.send("Page.screencastFrameAck", { sessionId: f.sessionId }); } catch {}
  });
  await cdp.send("Page.startScreencast", { format: "jpeg", quality: 92, maxWidth: 780, maxHeight: 1688, everyNthFrame: 1 });
  await pp.waitForTimeout(1200);
  for (let i = 0; i < 12; i++) { await pp.mouse.wheel(0, 45); await pp.waitForTimeout(60); }
  await pp.waitForTimeout(2500);
  await cdp.send("Page.stopScreencast");
  fs.writeFileSync(path.join(dir, "log.json"), JSON.stringify({ frames, marks: { start: 0, end: now() }, mouse: [] }, null, 1));
  console.log("M frames", frames.length);
  await pctx.close();
}

await browser.close();

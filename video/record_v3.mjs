// Screen recording of the running SkyBlink app for the demo video (real app, real SPHEREx data).
// Three takes: A = EN home -> Epsilon Indi card -> Blink (zoom) -> Difference; B = UZ viewer; C = RU viewer + Simple mode.
// Headless Chrome screencast frames + logged cursor and marks; video/build_video_v3.py cuts them to the voice.
// Usage: cd C:\skyblink_video && node record_v3.mjs   (needs playwright-core there, app on :3010)
// Developed with SI assistance (Claude); reviewed by team #1.
import { chromium } from "playwright-core";
import fs from "node:fs";
import path from "node:path";

const BASE = process.env.SKYBLINK_URL || "http://localhost:3010";
const OUT = process.env.REC_DIR || "C:\\skyblink_video\\v3\\rec";
const EPS = "ra=331.04383&dec=-56.78269&fov=300&det=6&name=Epsilon%20Indi%20B";
fs.rmSync(OUT, { recursive: true, force: true });

const browser = await chromium.launch({ channel: "chrome", headless: true });
const context = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
await context.addInitScript(() => { try { localStorage.setItem("skyblink_onboarding_done", "1"); } catch {} });
const page = await context.newPage();
for (const p of ["/en", `/en/view?${EPS}&mode=frames`, `/uz/view?${EPS}&mode=diff`, `/ru/view?${EPS}&mode=diff`]) {
  await page.goto(BASE + p, { waitUntil: "networkidle", timeout: 120000 });
}

async function take(name, setupUrl, script) {
  const dir = path.join(OUT, name);
  fs.mkdirSync(path.join(dir, "frames"), { recursive: true });
  await page.goto(BASE + setupUrl, { waitUntil: "networkidle", timeout: 120000 });
  await page.waitForTimeout(1500);
  const cdp = await context.newCDPSession(page);
  const frames = [], marks = {}, mouse = [];
  let t0 = null;
  const wall0 = Date.now();
  const now = () => (Date.now() - wall0) / 1000;
  cdp.on("Page.screencastFrame", async (f) => {
    const t = now();
    if (t0 === null) t0 = t;
    const fn = `f${String(frames.length).padStart(5, "0")}.jpg`;
    fs.writeFileSync(path.join(dir, "frames", fn), Buffer.from(f.data, "base64"));
    frames.push({ t, name: fn });
    try { await cdp.send("Page.screencastFrameAck", { sessionId: f.sessionId }); } catch {}
  });
  await cdp.send("Page.startScreencast", { format: "jpeg", quality: 92, maxWidth: 1920, maxHeight: 1080, everyNthFrame: 1 });
  let mx = 1300, my = 820;
  const api = {
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
  api.hoverEl = async (loc, ms = 700) => { const b = await loc.boundingBox(); await api.moveTo(b.x + b.width / 2, b.y + b.height / 2, ms); };
  api.clickEl = async (loc, ms = 700) => { await api.hoverEl(loc, ms); await api.click(); };
  await api.idle(300);
  await script(api);
  await cdp.send("Page.stopScreencast");
  await page.waitForTimeout(300);
  fs.writeFileSync(path.join(dir, "log.json"), JSON.stringify({ frames, marks, mouse }, null, 1));
  console.log(name, "frames", frames.length, "last", frames.at(-1)?.t.toFixed(2));
}

await take("A", "/en", async (a) => {
  a.mark("home");
  await a.idle(4600);
  a.mark("hover");
  await a.hoverEl(page.getByText("Epsilon Indi Ba/Bb").first(), 900);
  await a.idle(700);
  a.mark("click");
  await a.click();
  await page.waitForURL(/\/view/, { timeout: 60000 });
  await page.getByRole("button", { name: "Difference", exact: true }).first().waitFor({ timeout: 60000 });
  await page.waitForTimeout(300);
  // the card opens Difference (its default); the flipbook is the Blink view
  await a.clickEl(page.getByRole("button", { name: "Blink", exact: true }).first(), 500);
  await a.idle(300);
  const canvas = page.locator("canvas").first();
  await a.hoverEl(canvas, 500);
  a.mark("viewer");
  for (let i = 0; i < 2; i++) { await page.keyboard.press("+"); await a.idle(250); }
  const play = page.getByRole("button", { name: /play/i }).first();
  if (await play.count()) { try { await a.clickEl(play, 600); } catch {} }
  await a.idle(5200);
  a.mark("diff");
  await a.clickEl(page.getByRole("button", { name: "Difference", exact: true }).first(), 600);
  await a.idle(300);
  await a.moveTo(1320, 760, 700);
  await a.idle(4500);
  a.mark("end");
});

await take("B", `/uz/view?${EPS}&mode=diff`, async (a) => {
  for (let i = 0; i < 2; i++) { await page.keyboard.press("+"); await page.waitForTimeout(150); }
  a.mark("start");
  await a.idle(2500);
  a.mark("end");
});

await take("C", `/ru/view?${EPS}&mode=diff`, async (a) => {
  for (let i = 0; i < 2; i++) { await page.keyboard.press("+"); await page.waitForTimeout(150); }
  a.mark("start");
  await a.idle(700);
  const simple = page.locator("button[aria-pressed]").filter({ hasText: /Эксперт|Простой/ }).first();
  await a.hoverEl(simple, 600);
  a.mark("simple");
  await a.click();
  await a.idle(2500);
  a.mark("end");
});

await browser.close();

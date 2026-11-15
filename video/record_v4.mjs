// Screen recording of the running SkyBlink app for the demo video (real app, real SPHEREx data).
// Feature takes for narration v4: D = band slider (all wavelengths), E = Spectrum tab, F = Light curve tab, G = "I found something!".
// Headless Chrome screencast frames + logged cursor and marks; video/build_video_v3.py cuts them to the voice.
// Usage: cd C:\skyblink_video && node record_v3.mjs   (needs playwright-core there, app on :3010)
// Developed with SI assistance (Claude); reviewed by team #1.
import { chromium } from "playwright-core";
import fs from "node:fs";
import path from "node:path";

const BASE = process.env.SKYBLINK_URL || "http://localhost:3010";
const OUT = process.env.REC_DIR || "C:\\skyblink_video\\v3\\rec4";
const EPS = "ra=331.04383&dec=-56.78269&fov=300&det=6&name=Epsilon%20Indi%20B";
for (const t of (process.env.TAKES || "D,E,F,G").split(",")) fs.rmSync(path.join(OUT, t), { recursive: true, force: true });

const browser = await chromium.launch({ channel: "chrome", headless: true });
const context = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
await context.addInitScript(() => { try { localStorage.setItem("skyblink_onboarding_done", "1"); } catch {} });
const page = await context.newPage();
for (const p of ["/en", `/en/view?${EPS}&mode=frames`, `/en/view?${EPS.replace("det=6", "det=all")}&mode=sum`]) {
  await page.goto(BASE + p, { waitUntil: "networkidle", timeout: 120000 });
}

const WANT = (process.env.TAKES || "D,E,F,G").split(",");
async function take(name, setupUrl, script) {
  if (!WANT.includes(name)) return;
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


await take("D", `/en/view?${EPS.replace("det=6", "det=all")}&mode=sum`, async (a) => {
  await page.evaluate(() => window.scrollTo(0, 330));
  await page.waitForTimeout(400);
  const buttons = page.locator('input[type="range"]').locator("xpath=..").locator("button");
  const n = await buttons.count();
  await a.hoverEl(buttons.nth(0), 600);
  a.mark("start");
  for (let i = 1; i < n; i++) {
    await a.clickEl(buttons.nth(i), 260);
    await a.idle(520);
  }
  a.mark("end");
  await a.idle(500);
});

for (const [name, label, build] of [["E", "Spectrum", /Build spectrum/], ["F", "Light curve", /Measure brightness over time/]]) {
  await take(name, `/en/view?${EPS}&mode=diff`, async (a) => {
    await page.evaluate(() => window.scrollTo(0, 420));
    await page.waitForTimeout(400);
    const tab = page.getByRole("tab", { name: label }).or(page.getByRole("button", { name: label, exact: true })).first();
    a.mark("start");
    await a.clickEl(tab, 600);
    await a.idle(250);
    await a.clickEl(page.getByRole("button", { name: build }).first(), 500);
    a.mark("built");
    await a.idle(300);
    for (let i = 0; i < 10; i++) { await page.mouse.wheel(0, 60); await a.idle(40); }
    await a.idle(3000);
    a.mark("end");
  });
}

await take("G", `/en/view?${EPS}&mode=diff`, async (a) => {
  for (let i = 0; i < 2; i++) { await page.keyboard.press("+"); await page.waitForTimeout(150); }
  const btn = page.getByRole("button", { name: /I found something/ }).first();
  a.mark("start");
  await a.clickEl(btn, 800);
  await a.idle(2800);
  a.mark("end");
});

await browser.close();

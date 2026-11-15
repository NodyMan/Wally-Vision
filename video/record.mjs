// Screen recording of the running SkyBlink app for the demo video (real app, real SPHEREx data).
// Headless Chrome screencast frames + logged cursor positions and scene marks; build_video.py assembles them.
// Usage: cd C:\skyblink_video && node <repo>\video\record.mjs   (needs playwright-core there, app on :3010)
// Developed with SI assistance (Claude); reviewed by team #1.
import { chromium } from "playwright-core";
import fs from "node:fs";
import path from "node:path";

const BASE = process.env.SKYBLINK_URL || "http://localhost:3010";
const OUT = process.env.REC_DIR || "C:\\skyblink_video\\rec";
fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(path.join(OUT, "frames"), { recursive: true });

const browser = await chromium.launch({ channel: "chrome", headless: true });
const context = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
await context.addInitScript(() => {
  try { localStorage.setItem("skyblink_onboarding_done", "1"); } catch {}
});
const page = await context.newPage();

// warm the dev server (first compile is slow) before the recording starts
for (const p of ["/en", "/en/view?ra=331.04383&dec=-56.78269&fov=300&det=6&mode=diff&name=Epsilon%20Indi%20B", "/ru/view?ra=331.04383&dec=-56.78269&fov=300&det=6&mode=diff&name=Epsilon%20Indi%20B"]) {
  await page.goto(BASE + p, { waitUntil: "networkidle", timeout: 120000 });
}
await page.goto(BASE + "/en", { waitUntil: "networkidle" });
await page.waitForTimeout(800);

const cdp = await context.newCDPSession(page);
const frames = [];
let t0 = null;
cdp.on("Page.screencastFrame", async (f) => {
  const ts = f.metadata.timestamp; // seconds
  if (t0 === null) t0 = ts;
  const name = `f${String(frames.length).padStart(5, "0")}.jpg`;
  fs.writeFileSync(path.join(OUT, "frames", name), Buffer.from(f.data, "base64"));
  frames.push({ t: ts - t0, name });
  try { await cdp.send("Page.screencastFrameAck", { sessionId: f.sessionId }); } catch {}
});
const wall0 = Date.now();
await cdp.send("Page.startScreencast", { format: "jpeg", quality: 92, maxWidth: 1920, maxHeight: 1080, everyNthFrame: 1 });
const now = () => (Date.now() - wall0) / 1000;

const marks = {};
const mouse = [];
let mx = 960, my = 700;
const mark = (k) => { marks[k] = now(); console.log(k, marks[k].toFixed(2)); };
async function moveTo(x, y, ms = 700) {
  const steps = Math.max(8, Math.round(ms / 16));
  const sx = mx, sy = my;
  for (let i = 1; i <= steps; i++) {
    const e = i / steps, k = e * e * (3 - 2 * e);
    mx = sx + (x - sx) * k; my = sy + (y - sy) * k;
    await page.mouse.move(mx, my);
    mouse.push({ t: now(), x: mx, y: my });
    await page.waitForTimeout(ms / steps);
  }
}
async function clickEl(loc, ms = 700) {
  const b = await loc.boundingBox();
  await moveTo(b.x + b.width / 2, b.y + b.height / 2, ms);
  mouse.push({ t: now(), x: mx, y: my, click: true });
  await page.mouse.down(); await page.mouse.up();
}
const idle = async (ms) => { const end = Date.now() + ms; while (Date.now() < end) { mouse.push({ t: now(), x: mx, y: my }); await page.waitForTimeout(50); } };

// 1. home
mark("home");
await idle(1200);
const input = page.locator("form input").first();
await clickEl(input, 800);
await page.keyboard.type("Epsilon Indi", { delay: 90 });
await idle(500);
// 2. pick the preset card (the cached, curated field)
mark("card");
await clickEl(page.getByText("Epsilon Indi Ba/Bb").first(), 900);
await page.waitForURL(/\/view/, { timeout: 60000 });
await page.getByRole("button", { name: "Blink", exact: true }).first().waitFor({ timeout: 60000 });
await page.waitForTimeout(400);
// 3. blink
mark("blink");
await clickEl(page.getByRole("button", { name: "Blink", exact: true }).first(), 700);
await page.waitForTimeout(300);
const play = page.getByRole("button", { name: /play/i }).first();
if (await play.count()) { try { await clickEl(play, 600); } catch {} }
await idle(5200);
// 4. difference
mark("diff");
await clickEl(page.getByRole("button", { name: "Difference", exact: true }).first(), 700);
await idle(1200);
const readout = page.getByText("Measured shift").last();
if (await readout.count()) { try { const b = await readout.boundingBox(); await moveTo(b.x + b.width + 120, b.y + 8, 900); } catch {} }
await idle(6500);
// 5. language
mark("lang");
await clickEl(page.getByRole("button", { name: "RU", exact: true }).first(), 800);
await idle(4000);
mark("end");

await cdp.send("Page.stopScreencast");
await page.waitForTimeout(300);
fs.writeFileSync(path.join(OUT, "log.json"), JSON.stringify({ frames, marks, mouse, wallVsScreencast: "marks/mouse use wall clock from screencast start" }, null, 1));
console.log("frames", frames.length, "duration", frames.at(-1)?.t.toFixed(2));
await browser.close();

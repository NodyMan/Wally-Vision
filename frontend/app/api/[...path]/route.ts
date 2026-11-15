/**
 * Demo API for a deployment without the Python backend (Vercel only).
 * Answers the five preset fields from real results exported by backend/scripts/export_demo_api.py
 * (lib/demo/demo-data.json; frames are static files in public/api/frame/). Anything else gets the same
 * honest error the backend gives when downloads are switched off — never a made-up result.
 * Used only when NEXT_PUBLIC_API_URL is not set in a production build (see lib/api/platform.ts).
 * Developed with SI assistance (Claude); reviewed by team #1.
 */
import { NextResponse, type NextRequest } from "next/server";
import demo from "@/lib/demo/demo-data.json";

type Center = number[];
type BlinkAnswer = { mode: string; fov_arcsec: number; frames: { detector: number }[] };
type Science = { status: number; body: unknown; detector: number | null };
type Target = {
  slug: string;
  centers: Center[];
  blinks: BlinkAnswer[];
  science: Record<string, Science>;
};
type Preset = { slug: string; ra: number; dec: number; fov: number; title: Record<string, string> };

const data = demo as unknown as { presets: Preset[]; targets: Target[] };
const MATCH_ARCSEC = 20;

const json = (body: unknown, status = 200) =>
  NextResponse.json(body, { status, headers: { "Cache-Control": "no-store" } });

function sepArcsec(ra1: number, dec1: number, ra2: number, dec2: number): number {
  const dra = ((ra1 - ra2 + 540) % 360) - 180;
  const dec = ((dec1 + dec2) / 2) * (Math.PI / 180);
  return 3600 * Math.hypot(dra * Math.cos(dec), dec1 - dec2);
}

function findTarget(ra: number, dec: number): Target | undefined {
  if (!Number.isFinite(ra) || !Number.isFinite(dec)) return undefined;
  return data.targets.find((t) => t.centers.some(([cra, cdec]) => sepArcsec(ra, dec, cra, cdec) <= MATCH_ARCSEC));
}

const num = (q: URLSearchParams, k: string) => Number(q.get(k));
const offline = () => json({ error_code: "cold_disabled" }, 503);

// names people type for the five fields (any case, spaces and punctuation ignored)
const ALIASES: Record<string, string[]> = {
  "barnards-star": ["barnard", "barnards", "barnardsstar", "gj699", "v2500oph"],
  "epsilon-indi-b": ["epsilonindi", "epsilonindib", "epsindb", "epsind", "epsilonindibab", "epsilonindibabb"],
  "wise-0855": ["wise0855", "wise08550714", "wisej085510830714", "wisej08550714"],
  "rw-aurigae": ["rwaur", "rwaurigae"],
  "r-draconis": ["rdra", "rdraconis"],
};
const norm = (s: string) => s.toLowerCase().normalize("NFKD").replace(/[^a-z0-9а-яё]/g, "");

function parseCoords(q: string): [number, number] | null {
  const dec = q.trim().match(/^(-?\d+(?:\.\d+)?)[\s,]+([+-]?\d+(?:\.\d+)?)$/);
  if (dec) return [Number(dec[1]), Number(dec[2])];
  const sex = q
    .trim()
    .match(/^(\d{1,2})[h:\s](\d{1,2})[m:\s](\d{1,2}(?:\.\d+)?)s?\s+([+-]?)(\d{1,2})[d°:\s](\d{1,2})[m′':\s](\d{1,2}(?:\.\d+)?)[s″"]?$/i);
  if (!sex) return null;
  const ra = 15 * (Number(sex[1]) + Number(sex[2]) / 60 + Number(sex[3]) / 3600);
  const d = Number(sex[5]) + Number(sex[6]) / 60 + Number(sex[7]) / 3600;
  return [ra, sex[4] === "-" ? -d : d];
}

function resolve(q: string) {
  const coords = parseCoords(q);
  if (coords && coords[0] >= 0 && coords[0] < 360 && Math.abs(coords[1]) <= 90) {
    return json({ ra: coords[0], dec: coords[1], name: q.trim(), source: "coordinates" });
  }
  const n = norm(q);
  for (const p of data.presets) {
    const names = [...(ALIASES[p.slug] ?? []), ...Object.values(p.title).map(norm)];
    if (n && names.some((a) => a === n || (n.length >= 4 && a.startsWith(n)))) {
      return json({ ra: p.ra, dec: p.dec, name: p.title.en, source: "preset" });
    }
  }
  return json({ code: "not_found", detail: `Could not resolve '${q}' (this demo knows the five featured objects)` }, 404);
}

export async function GET(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  const route = path.join("/");
  const q = req.nextUrl.searchParams;

  if (route === "health") return json({ status: "ok", mode: "demo" });
  if (route === "presets") return json(data.presets);
  if (route === "resolve") return resolve(q.get("q") ?? "");
  if (route === "findings") return json([]);
  if (route === "catalog") return json({ error_code: "catalog_unavailable" }, 502);

  if (route === "blink") {
    const target = findTarget(num(q, "ra"), num(q, "dec"));
    const fov = num(q, "fov") || 300;
    const det = q.get("detector") ?? "";
    const mode = q.get("mode") ?? "frames";
    const answer = target?.blinks.find((b) => {
      if (b.mode !== mode || b.fov_arcsec !== fov) return false;
      const dets = new Set(b.frames.map((f) => f.detector));
      return det === "all" ? dets.size > 1 : dets.size === 1 && dets.has(Number(det));
    });
    if (answer) return json(answer);
    return q.get("only_cached") === "1" ? new NextResponse(null, { status: 204 }) : offline();
  }

  if (route === "lightcurve" || route === "spectrum") {
    const target = findTarget(num(q, "cra"), num(q, "cdec")) ?? findTarget(num(q, "ra"), num(q, "dec"));
    const s = target?.science[route];
    const fov = num(q, "fov") || 300;
    const preset = target && data.presets.find((p) => p.slug === target.slug);
    if (s && preset && preset.fov === fov && (s.detector === null || s.detector === num(q, "detector"))) {
      return json(s.body, s.status);
    }
    return offline();
  }

  return json({ error_code: "not_found" }, 404);
}

export async function POST(_req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  if (path.join("/") === "findings") {
    // no database in the demo: the browser keeps the finding in its local list
    return json({ code: "demo_readonly", detail: "This demo has no server database." }, 503);
  }
  return json({ error_code: "not_found" }, 404);
}

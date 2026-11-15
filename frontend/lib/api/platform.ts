// NEXT_PUBLIC_API_URL = the Django backend. Without it, a production build (Vercel) uses its own demo API
// (app/api/[...path]: real results for the five featured fields); local development keeps localhost:8000.
const CONFIGURED_API = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
const IN_BROWSER_PROD = process.env.NODE_ENV === "production" && typeof window !== "undefined";

export let API_BASE_URL =
  CONFIGURED_API || (IN_BROWSER_PROD ? window.location.origin : "http://localhost:8000");

/**
 * Resolves once the API base is final. In a production browser with a configured backend, the backend is
 * asked for /api/health first; if it does not answer within 6 s (paused, asleep, gone), the site falls back
 * to its own demo API. Every API call awaits this before building its URL.
 */
export const apiReady: Promise<void> =
  CONFIGURED_API && IN_BROWSER_PROD
    ? fetch(`${CONFIGURED_API}/api/health`, { cache: "no-store", signal: AbortSignal.timeout(6000) })
        .then((r) => {
          if (!r.ok) throw new Error(`backend ${r.status}`);
        })
        .catch(() => {
          API_BASE_URL = window.location.origin;
        })
    : Promise.resolve();

export type HealthResponse = {
  status: string;
};

export type ResolveResponse = {
  ra: number;
  dec: number;
  name: string;
  source: string;
};

export type LocalizedText = {
  en: string;
  ru: string;
  uz: string;
};

export type PresetItem = {
  slug: string;
  ra: number;
  dec: number;
  type: "brown_dwarf" | "high_pm_star" | "variable_star";
  fov: number;
  default_mode: "frames" | "diff" | "sum";
  default_detector?: 1 | 2 | 3 | 4 | 5 | 6; // band chosen by #1 for this target (D6 for brown dwarfs)
  title: LocalizedText;
  short: LocalizedText;
  what_you_see: LocalizedText;
};

export type FindingItem = {
  id: number | string;
  ra: number;
  dec: number;
  note: string;
  nickname: string;
  created_at: string;
  status: "new" | "reviewed";
};

export type FindingSubmitPayload = {
  ra: number;
  dec: number;
  note: string;
  nickname?: string;
  website?: string;
};

const MY_FINDINGS_STORAGE_KEY = "skyblink_my_findings";

export async function fetchHealth(): Promise<HealthResponse> {
  await apiReady;
  const res = await fetch(`${API_BASE_URL}/api/health`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Health check failed: ${res.status}`);
  }
  return res.json();
}

export async function resolveTarget(query: string): Promise<ResolveResponse> {
  await apiReady;
  const url = new URL(`${API_BASE_URL}/api/resolve`);
  url.searchParams.set("q", query);
  let res: Response;
  try {
    res = await fetch(url.toString(), { cache: "no-store" });
  } catch {
    throw new Error("network_error");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data?.code || "not_found");
  }
  return data;
}

export async function fetchPresets(): Promise<PresetItem[]> {
  await apiReady;
  const res = await fetch(`${API_BASE_URL}/api/presets`, {
    next: { revalidate: 300 },
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch presets: ${res.status}`);
  }
  return res.json();
}

export async function fetchFindings(): Promise<FindingItem[]> {
  await apiReady;
  const res = await fetch(`${API_BASE_URL}/api/findings`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch findings: ${res.status}`);
  }
  return res.json();
}

export async function submitFinding(
  payload: FindingSubmitPayload
): Promise<FindingItem> {
  let res: Response;
  try {
    await apiReady;
    res = await fetch(`${API_BASE_URL}/api/findings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    throw new Error("network_error");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data?.code || "unknown");
  }
  return data;
}

function isValidFindingItem(item: unknown): item is FindingItem {
  if (!item || typeof item !== "object") return false;
  const candidate = item as Record<string, unknown>;
  return (
    typeof candidate.id === "number" &&
    Number.isFinite(candidate.ra) &&
    Number.isFinite(candidate.dec) &&
    typeof candidate.note === "string"
  );
}

export function getMyFindings(): FindingItem[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(MY_FINDINGS_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter(isValidFindingItem) : [];
  } catch {
    return [];
  }
}

export function saveMyFinding(item: FindingItem): void {
  if (typeof window === "undefined") return;
  try {
    const existing = getMyFindings();
    const updated = [item, ...existing.filter((x) => x.id !== item.id)].slice(
      0,
      50
    );
    window.localStorage.setItem(MY_FINDINGS_STORAGE_KEY, JSON.stringify(updated));
  } catch {
    // Ignore storage quota errors
  }
}

"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import {
  API_BASE_URL,
  fetchHealth,
  resolveTarget,
  type PresetItem,
} from "@/lib/api/platform";
import type { Locale } from "@/i18n/routing";
import { Search, ArrowRight, Activity, Compass } from "lucide-react";

type HomeClientProps = {
  initialPresets: PresetItem[];
};

// Card thumbnails are real SPHEREx frames. The request is cache-only (`only_cached=1`), so opening the
// home page never starts a download from NASA; a preset that is not warmed yet keeps the placeholder.
const ENABLE_BLINK_PREVIEWS =
  process.env.NEXT_PUBLIC_ENABLE_BLINK_PREVIEWS !== "false";

export function HomeClient({ initialPresets }: HomeClientProps) {
  const tHome = useTranslations("home");
  const tPresets = useTranslations("presets");
  const tStatus = useTranslations("common.status");
  const tErrors = useTranslations("errors");
  const locale = useLocale() as Locale;
  const router = useRouter();

  const [query, setQuery] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [apiState, setApiState] = useState<"waking" | "online" | "offline">("waking");
  const [previews, setPreviews] = useState<Record<string, string>>({});

  const starExample = tHome("hero.starExample");
  // a short list keeps the search area calm; coordinates are still accepted in the field
  const quickExamples = ["WISE 0855", starExample, "133.795 -7.245"];

  useEffect(() => {
    let active = true;
    const retryDelaysMs = [0, 1500, 3000];

    async function checkBackend() {
      for (let i = 0; i < retryDelaysMs.length; i++) {
        if (!active) return;
        if (retryDelaysMs[i] > 0) {
          await new Promise((r) => window.setTimeout(r, retryDelaysMs[i]));
        }
        if (!active) return;
        try {
          await fetchHealth();
          if (!active) return;
          setApiState("online");

          if (ENABLE_BLINK_PREVIEWS) {
            initialPresets.forEach((preset) => {
              const url = new URL(`${API_BASE_URL}/api/blink`);
              url.searchParams.set("ra", String(preset.ra));
              url.searchParams.set("dec", String(preset.dec));
              url.searchParams.set("fov", String(preset.fov));
              url.searchParams.set("mode", preset.default_mode);
              url.searchParams.set("detector", String(preset.default_detector ?? 6));
              url.searchParams.set("only_cached", "1");
              fetch(url.toString())
                .then((r) => (r.status === 200 ? r.json() : null))
                .then((data) => {
                  // the "latest minus earliest" frame shows the motion best; otherwise the first frame
                  const frames: { url?: string; kind?: string }[] = data?.frames ?? [];
                  const firstUrl = (frames.find((f) => f.kind === "diff_pair") ?? frames[0])?.url;
                  if (active && typeof firstUrl === "string") {
                    const fullUrl = firstUrl.startsWith("http")
                      ? firstUrl
                      : `${API_BASE_URL}${firstUrl}`;
                    setPreviews((prev) => ({ ...prev, [preset.slug]: fullUrl }));
                  }
                })
                .catch(() => {});
            });
          }
          return;
        } catch {
          if (i === retryDelaysMs.length - 1 && active) {
            setApiState("offline");
          }
        }
      }
    }

    void checkBackend();
    return () => {
      active = false;
    };
  }, [initialPresets]);

  async function resolveAndOpen(targetQuery: string) {
    const trimmed = targetQuery.trim();
    if (!trimmed || submitting) return;

    setSubmitting(true);
    setErrorCode(null);
    try {
      const resolved = await resolveTarget(trimmed);
      // a search that lands on one of the five presets opens it with the preset's own mode and band
      const preset = resolved.source === "preset"
        ? initialPresets.find((p) => Math.abs(p.ra - resolved.ra) < 1e-4 && Math.abs(p.dec - resolved.dec) < 1e-4)
        : undefined;
      if (preset) {
        openPreset(preset);
        return;
      }
      const params = new URLSearchParams({
        ra: resolved.ra.toFixed(6),
        dec: resolved.dec.toFixed(6),
        name: resolved.name || trimmed,
      });
      router.push(`/view?${params.toString()}`);
    } catch (err) {
      const code = err instanceof Error ? err.message : "unknown";
      setErrorCode(code);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    await resolveAndOpen(query);
  }

  function openPreset(preset: PresetItem) {
    const title = preset.title[locale] || preset.title.en;
    const params = new URLSearchParams({
      ra: preset.ra.toFixed(6),
      dec: preset.dec.toFixed(6),
      fov: String(preset.fov),
      mode: preset.default_mode,
      det: String(preset.default_detector ?? 6),
      name: title,
    });
    router.push(`/view?${params.toString()}`);
  }

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-10 px-4 py-10 sm:py-14">
      {/* Hero + search: one field, nothing else competing for attention */}
      <section className="flex flex-col gap-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <span className="rounded-full bg-sky-950 px-3 py-1 text-xs font-medium text-sky-600">
            {tHome("hero.badge")}
          </span>
          <span className="hud-label inline-flex items-center gap-1.5" aria-live="polite">
            <Activity
              className={`h-3.5 w-3.5 ${
                apiState === "online" ? "text-sky-400" : apiState === "waking" ? "animate-pulse text-amber-500" : "text-rose-500"
              }`}
              aria-hidden="true"
            />
            {apiState === "online" ? tStatus("apiOnline") : apiState === "waking" ? tStatus("apiWaking") : tStatus("apiOffline")}
          </span>
        </div>

        <h1 className="max-w-4xl text-balance text-4xl font-light leading-[1.05] tracking-tight text-white sm:text-6xl">
          {tHome("hero.title")}
        </h1>
        <p className="max-w-2xl text-base text-slate-400 sm:text-lg">{tHome("hero.subtitle")}</p>

        <form onSubmit={handleSearch} className="card flex flex-col gap-2 p-2 sm:flex-row">
          <label htmlFor="skyblink-search" className="sr-only">{tHome("hero.searchLabel")}</label>
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" aria-hidden="true" />
            <input
              id="skyblink-search"
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={tHome("hero.searchPlaceholder")}
              className="w-full rounded-xl bg-transparent py-3.5 pl-12 pr-4 text-base text-white placeholder:text-slate-500 focus:outline-none"
            />
          </div>
          <button
            type="submit"
            disabled={submitting || !query.trim()}
            aria-busy={submitting}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-sky-500 px-6 py-3.5 text-sm font-semibold text-slate-950 transition-colors hover:bg-sky-600 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <span>{submitting ? tHome("hero.searching") : tHome("hero.searchButton")}</span>
            <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </button>
        </form>

        {errorCode && (
          <p role="alert" className="text-sm text-rose-600">
            {tErrors.has(errorCode) ? tErrors(errorCode) : tErrors("unknown")}
          </p>
        )}

        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400">
          <span>{tHome("hero.examplesLabel")}</span>
          {quickExamples.map((example) => (
            <button
              key={example}
              type="button"
              disabled={submitting}
              onClick={() => {
                setQuery(example);
                void resolveAndOpen(example);
              }}
              className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-slate-300 transition-colors hover:border-sky-400 hover:text-sky-600 disabled:opacity-50"
            >
              {example}
            </button>
          ))}
        </div>
      </section>

      {/* The five challenge objects */}
      <section aria-labelledby="presets-heading" className="flex flex-col gap-5">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <h2 id="presets-heading" className="text-2xl font-light text-white sm:text-3xl">{tHome("presets.title")}</h2>
          <p className="text-sm text-slate-400">{tHome("presets.subtitle")}</p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {initialPresets.map((preset) => {
            const title = preset.title[locale] || preset.title.en;
            const short = preset.short[locale] || preset.short.en;
            const previewUrl = previews[preset.slug];
            return (
              <button
                key={preset.slug}
                type="button"
                onClick={() => openPreset(preset)}
                className="card group flex flex-col gap-4 p-3 text-left transition-shadow hover:shadow-lg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-400"
              >
                <div className="relative flex aspect-[16/10] items-center justify-center overflow-hidden rounded-xl bg-black">
                  {previewUrl ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={previewUrl} alt="" className="h-full w-full object-cover [image-rendering:pixelated]" />
                  ) : (
                    <Compass className="h-6 w-6 text-neutral-500" aria-hidden="true" />
                  )}
                  <span className="absolute left-2 top-2 rounded-full bg-neutral-50/90 px-2.5 py-0.5 text-[11px] font-medium text-neutral-800">
                    {tPresets(`types.${preset.type}`)}
                  </span>
                </div>
                <div className="flex flex-1 flex-col gap-1 px-1">
                  <h3 className="text-lg font-semibold text-white">{title}</h3>
                  <p className="line-clamp-2 text-sm text-slate-400">{short}</p>
                </div>
                <div className="flex items-center justify-between px-1 pb-1">
                  <span className="hud-label">{tPresets(`modes.${preset.default_mode}`)} · D{preset.default_detector ?? 6}</span>
                  <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-sky-950 text-sky-600 transition-colors group-hover:bg-sky-500 group-hover:text-slate-950">
                    <ArrowRight className="h-4 w-4" aria-hidden="true" />
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      </section>
    </div>
  );
}

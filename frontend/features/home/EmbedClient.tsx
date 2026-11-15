"use client";

import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { ExternalLink, Telescope } from "lucide-react";
import { ViewPage } from "@/features/viewer/ViewPage";

/**
 * Minimal iframe-ready embed shell (#3) with #1's player mounted in it.
 * Takes the same URL parameters as /view: ra, dec, name, fov, mode, det, t.
 */
export function EmbedClient() {
  const t = useTranslations("common");
  const searchParams = useSearchParams();

  const name = searchParams.get("name") || "SkyBlink";
  const mode = searchParams.get("mode") || "frames";
  const hasTarget = searchParams.has("ra") && searchParams.has("dec");

  return (
    <div className="flex min-h-[380px] flex-col bg-slate-950 text-slate-100">
      <div className="flex items-center justify-between gap-2 border-b border-slate-800 px-4 py-3">
        <div className="flex min-w-0 items-center gap-2">
          <Telescope className="h-4 w-4 shrink-0 text-sky-400" aria-hidden="true" />
          <span className="truncate text-sm font-semibold text-white">{name}</span>
          <span className="rounded bg-slate-800 px-2 py-0.5 font-mono text-[11px] text-sky-600">
            {mode.toUpperCase()}
          </span>
        </div>

        <Link
          href={hasTarget ? `/view?${searchParams.toString()}` : "/"}
          target="_blank"
          className="inline-flex shrink-0 items-center gap-1 rounded-lg bg-sky-500 px-3 py-1 text-xs font-semibold text-slate-950 hover:bg-sky-400"
        >
          <span>{t("embed.openFull")}</span>
          <ExternalLink className="h-3 w-3" aria-hidden="true" />
        </Link>
      </div>

      <ViewPage compact />
    </div>
  );
}

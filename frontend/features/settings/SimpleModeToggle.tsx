"use client";

import { useTranslations } from "next-intl";
import { Sparkles, SlidersHorizontal } from "lucide-react";
import { useSimpleModeStore } from "./simpleModeStore";

export function SimpleModeToggle() {
  const t = useTranslations("common.simpleMode");
  const simpleMode = useSimpleModeStore((s) => s.simpleMode);
  const toggleSimpleMode = useSimpleModeStore((s) => s.toggleSimpleMode);

  return (
    <button
      type="button"
      onClick={toggleSimpleMode}
      aria-pressed={simpleMode}
      title={t("hint")}
      className="inline-flex items-center gap-1 rounded-full border border-slate-700 bg-slate-900/80 px-2.5 py-1 text-xs font-medium text-slate-200 transition-colors hover:border-sky-500/60 hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-400 sm:gap-1.5 sm:px-3 sm:py-1.5"
    >
      {simpleMode ? (
        <Sparkles className="h-3.5 w-3.5 text-sky-400" aria-hidden="true" />
      ) : (
        <SlidersHorizontal
          className="h-3.5 w-3.5 text-amber-400"
          aria-hidden="true"
        />
      )}
      <span>{simpleMode ? t("simple") : t("expert")}</span>
    </button>
  );
}

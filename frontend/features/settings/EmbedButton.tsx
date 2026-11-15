"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Code2, Check } from "lucide-react";

type EmbedButtonProps = {
  ra: number;
  dec: number;
  fov?: number;
  mode?: "frames" | "diff" | "sum";
  name?: string;
};

/**
 * Toolbar action (#3) that copies a responsive <iframe> snippet for /embed.
 */
export function EmbedButton({
  ra,
  dec,
  fov = 300,
  mode = "frames",
  name,
}: EmbedButtonProps) {
  const t = useTranslations("common.embed");
  const locale = useLocale();
  const [copied, setCopied] = useState(false);
  const [fallbackSnippet, setFallbackSnippet] = useState<string | null>(null);

  async function handleCopy() {
    const origin =
      typeof window !== "undefined" ? window.location.origin : "https://skyblink.app";
    const params = new URLSearchParams({
      ra: ra.toFixed(6),
      dec: dec.toFixed(6),
      fov: String(fov),
      mode,
    });
    if (name) params.set("name", name);

    const src = `${origin}/${locale}/embed?${params.toString()}`;
    const snippet = `<iframe src="${src}" width="640" height="520" loading="lazy" style="border:0;border-radius:12px;" title="SkyBlink Viewer"></iframe>`;

    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(snippet);
        setFallbackSnippet(null);
        setCopied(true);
        window.setTimeout(() => setCopied(false), 2200);
        return;
      }
    } catch {
      // Fall through to execCommand fallback
    }

    try {
      const textarea = document.createElement("textarea");
      textarea.value = snippet;
      textarea.setAttribute("readonly", "");
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.select();
      const ok = document.execCommand("copy");
      document.body.removeChild(textarea);
      if (ok) {
        setFallbackSnippet(null);
        setCopied(true);
        window.setTimeout(() => setCopied(false), 2200);
        return;
      }
    } catch {
      // Ignore execCommand error and expose manual copy input
    }
    setFallbackSnippet(snippet);
  }

  return (
    <div className="inline-flex flex-col items-end gap-1.5">
      <button
        type="button"
        onClick={handleCopy}
        className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-medium text-slate-200 transition-colors hover:border-sky-500/60 hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-400"
      >
        {copied ? (
          <Check className="h-3.5 w-3.5 text-emerald-400" aria-hidden="true" />
        ) : (
          <Code2 className="h-3.5 w-3.5 text-sky-400" aria-hidden="true" />
        )}
        <span>{copied ? t("copied") : t("button")}</span>
      </button>
      {fallbackSnippet && (
        <div className="w-full max-w-xs rounded-lg border border-slate-700 bg-slate-950 p-2 text-xs text-slate-300">
          <p className="mb-1 text-amber-300">{t("copyFailed")}</p>
          <input
            type="text"
            readOnly
            value={fallbackSnippet}
            onFocus={(e) => e.currentTarget.select()}
            className="w-full rounded border border-slate-700 bg-slate-900 px-2 py-1 font-mono text-[11px] text-slate-100"
          />
        </div>
      )}
    </div>
  );
}

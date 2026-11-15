"use client";

import { useCallback, useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import {
  fetchFindings,
  getMyFindings,
  type FindingItem,
} from "@/lib/api/platform";
import { ReportFindingButton } from "./ReportFindingButton";
import { ExternalLink, RefreshCw, Sparkles } from "lucide-react";

export function FindingsClient() {
  const t = useTranslations("findings");
  const tCommon = useTranslations("common.status");
  const tErrors = useTranslations("errors");
  const locale = useLocale();

  const [tab, setTab] = useState<"community" | "mine">("community");
  const [community, setCommunity] = useState<FindingItem[]>([]);
  const [mine, setMine] = useState<FindingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);

  const loadCommunity = useCallback(() => {
    setLoading(true);
    setLoadError(false);
    return fetchFindings()
      .then((items) => {
        setCommunity(items);
      })
      .catch(() => {
        setLoadError(true);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    let active = true;
    const timer = window.setTimeout(() => {
      if (active) setMine(getMyFindings());
    }, 0);
    fetchFindings()
      .then((items) => {
        if (active) setCommunity(items);
      })
      .catch(() => {
        if (active) setLoadError(true);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, []);

  function handleCreated(item: FindingItem) {
    setCommunity((prev) => [item, ...prev]);
    setMine(getMyFindings());
  }

  function formatDate(iso: string) {
    try {
      return new Intl.DateTimeFormat(locale, {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(new Date(iso));
    } catch {
      return iso;
    }
  }

  const items = tab === "community" ? community : mine;

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 px-4 py-10">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white">{t("title")}</h1>
          <p className="mt-2 text-sm text-slate-300">{t("subtitle")}</p>
        </div>
        <ReportFindingButton onCreated={handleCreated} />
      </div>

      <div className="flex gap-2 border-b border-slate-800 pb-3" role="tablist">
        <button
          id="tab-community"
          type="button"
          role="tab"
          aria-selected={tab === "community"}
          aria-controls="findings-panel"
          onClick={() => setTab("community")}
          className={`rounded-full px-4 py-1.5 text-xs font-medium transition-colors ${
            tab === "community"
              ? "bg-sky-500 text-slate-950"
              : "bg-slate-900 text-slate-300 hover:text-white"
          }`}
        >
          {t("communityTab")} ({community.length})
        </button>
        <button
          id="tab-mine"
          type="button"
          role="tab"
          aria-selected={tab === "mine"}
          aria-controls="findings-panel"
          onClick={() => setTab("mine")}
          className={`rounded-full px-4 py-1.5 text-xs font-medium transition-colors ${
            tab === "mine"
              ? "bg-sky-500 text-slate-950"
              : "bg-slate-900 text-slate-300 hover:text-white"
          }`}
        >
          {t("myFindings")} ({mine.length})
        </button>
      </div>

      <div
        id="findings-panel"
        role="tabpanel"
        aria-labelledby={tab === "community" ? "tab-community" : "tab-mine"}
      >
        {loading && tab === "community" ? (
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-8 text-center text-sm text-slate-300">
            {tCommon("loading")}
          </div>
        ) : loadError && tab === "community" ? (
          <div
            role="alert"
            className="flex flex-col items-center gap-3 rounded-2xl border border-rose-500/30 bg-rose-500/10 p-6 text-center text-sm text-rose-300"
          >
            <p>{tErrors("network_error")}</p>
            <button
              type="button"
              onClick={loadCommunity}
              className="inline-flex items-center gap-1.5 rounded-lg border border-rose-400/40 bg-slate-950 px-3.5 py-1.5 text-xs font-medium text-white hover:border-rose-300"
            >
              <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
              <span>{tCommon("retry")}</span>
            </button>
          </div>
        ) : items.length === 0 ? (
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-8 text-center text-sm text-slate-300">
            {tab === "community" ? t("empty") : t("myEmpty")}
          </div>
        ) : (
          <div className="grid gap-4">
            {items.map((item) => (
              <article
                key={`${tab}-${item.id}`}
                className="flex flex-col justify-between gap-3 rounded-2xl border border-slate-800 bg-slate-900/60 p-5 sm:flex-row sm:items-center"
              >
                <div className="space-y-1.5">
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <span className="inline-flex items-center gap-1 rounded-full bg-sky-500/15 px-2.5 py-0.5 font-mono text-sky-600">
                      <Sparkles className="h-3 w-3" aria-hidden="true" />
                      {item.ra.toFixed(5)}, {item.dec.toFixed(5)}
                    </span>
                    <span className="rounded-full bg-slate-800 px-2 py-0.5 text-slate-300">
                      {t(`status.${item.status}`)}
                    </span>
                    <span className="text-slate-300">
                      {item.nickname || t("anonymous")}
                    </span>
                    <span className="text-slate-400">
                      · {formatDate(item.created_at)}
                    </span>
                  </div>
                  <p className="text-sm text-slate-200">{item.note}</p>
                </div>

                <Link
                  href={`/view?ra=${item.ra.toFixed(6)}&dec=${item.dec.toFixed(6)}`}
                  className="inline-flex shrink-0 items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-950 px-3.5 py-2 text-xs font-medium text-white transition-colors hover:border-sky-400 hover:text-sky-600"
                >
                  <span>{t("openInViewer")}</span>
                  <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                </Link>
              </article>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { HelpCircle, X, ChevronLeft, ChevronRight } from "lucide-react";

const TOUR_STORAGE_KEY = "skyblink_onboarding_done";
const TOTAL_STEPS = 4;

type TourProps = {
  autoOpen?: boolean;
};

/**
 * 4-step first-visit onboarding tour for /view (#3).
 */
export function Tour({ autoOpen = true }: TourProps) {
  const t = useTranslations("onboarding");
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(1);

  const triggerRef = useRef<HTMLButtonElement>(null);
  const nextRef = useRef<HTMLButtonElement>(null);

  const dismiss = useCallback(() => {
    setOpen(false);
    try {
      window.localStorage.setItem(TOUR_STORAGE_KEY, "1");
    } catch {
      // Ignore storage errors
    }
    window.setTimeout(() => triggerRef.current?.focus(), 0);
  }, []);

  useEffect(() => {
    if (!autoOpen || typeof window === "undefined") return;
    const timer = window.setTimeout(() => {
      try {
        const done = window.localStorage.getItem(TOUR_STORAGE_KEY);
        if (!done) {
          setOpen(true);
        }
      } catch {
        // Ignore storage errors
      }
    }, 0);
    return () => window.clearTimeout(timer);
  }, [autoOpen]);

  useEffect(() => {
    if (!open) return;
    nextRef.current?.focus();
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        dismiss();
      } else if (e.key === "ArrowRight") {
        setStep((s) => Math.min(TOTAL_STEPS, s + 1));
      } else if (e.key === "ArrowLeft") {
        setStep((s) => Math.max(1, s - 1));
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, dismiss]);

  function reopen() {
    setStep(1);
    setOpen(true);
  }

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        onClick={reopen}
        className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-medium text-slate-200 transition-colors hover:border-sky-500/60 hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-400"
      >
        <HelpCircle className="h-3.5 w-3.5 text-sky-400" aria-hidden="true" />
        <span>{t("replay")}</span>
      </button>

      {open && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="skyblink-tour-title"
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/75 p-4 backdrop-blur-sm"
        >
          <div className="w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <span className="rounded-full bg-sky-500/15 px-2.5 py-0.5 text-xs font-semibold text-sky-600">
                  {step} / {TOTAL_STEPS}
                </span>
                <div className="flex gap-1" aria-hidden="true">
                  {[1, 2, 3, 4].map((idx) => (
                    <span
                      key={idx}
                      className={`h-1.5 w-4 rounded-full ${
                        idx <= step ? "bg-sky-400" : "bg-slate-700"
                      }`}
                    />
                  ))}
                </div>
              </div>
              <button
                type="button"
                onClick={dismiss}
                aria-label={t("skip")}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white focus-visible:outline-2 focus-visible:outline-sky-400"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>

            <h2
              id="skyblink-tour-title"
              className="mt-4 text-lg font-semibold text-white"
            >
              {t(`steps.${step}.title`)}
            </h2>
            <p className="mt-2 text-sm leading-6 text-slate-300">
              {t(`steps.${step}.body`)}
            </p>

            <div className="mt-6 flex items-center justify-between gap-3">
              <button
                type="button"
                onClick={dismiss}
                className="text-xs font-medium text-slate-400 hover:text-white"
              >
                {t("skip")}
              </button>

              <div className="flex items-center gap-2">
                {step > 1 && (
                  <button
                    type="button"
                    onClick={() => setStep((s) => Math.max(1, s - 1))}
                    className="inline-flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-xs font-medium text-slate-200 hover:border-slate-500"
                  >
                    <ChevronLeft className="h-3.5 w-3.5" aria-hidden="true" />
                    <span>{t("back")}</span>
                  </button>
                )}

                {step < TOTAL_STEPS ? (
                  <button
                    ref={nextRef}
                    type="button"
                    onClick={() => setStep((s) => Math.min(TOTAL_STEPS, s + 1))}
                    className="inline-flex items-center gap-1 rounded-lg bg-sky-500 px-3.5 py-1.5 text-xs font-semibold text-slate-950 hover:bg-sky-400"
                  >
                    <span>{t("next")}</span>
                    <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
                  </button>
                ) : (
                  <button
                    ref={nextRef}
                    type="button"
                    onClick={dismiss}
                    className="rounded-lg bg-emerald-500 px-4 py-1.5 text-xs font-semibold text-white hover:bg-emerald-400"
                  >
                    {t("finish")}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

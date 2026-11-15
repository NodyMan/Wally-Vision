"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { CheckCircle2, HelpCircle, Pause, Play, SkipForward } from "lucide-react";

type Choice = "motion" | "variable" | "artifact";

type TrainingCase = {
  id: "1" | "2" | "3";
  answer: Choice;
};

const CASES: TrainingCase[] = [
  { id: "1", answer: "motion" },
  { id: "2", answer: "variable" },
  { id: "3", answer: "artifact" },
];

const EPOCHS = [0, 1, 2, 3];

export function PracticeSection() {
  const t = useTranslations("about.practice");
  const [epoch, setEpoch] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [selected, setSelected] = useState<Record<string, Choice | undefined>>({});

  useEffect(() => {
    if (!playing) return;
    const id = window.setInterval(() => {
      setEpoch((e) => (e + 1) % EPOCHS.length);
    }, 650);
    return () => window.clearInterval(id);
  }, [playing]);

  function renderSimulatedDot(caseId: "1" | "2" | "3") {
    if (caseId === "1") {
      // Moving object shifts smoothly across 4 epochs
      const x = 35 + epoch * 10;
      const y = 55 - epoch * 7;
      return <circle cx={x} cy={y} r={5} fill="#38bdf8" />;
    }
    if (caseId === "2") {
      // Variable star stays fixed and pulses brightness/radius
      const radii = [3, 6.5, 8, 4];
      const opacities = [0.45, 0.85, 1, 0.55];
      return (
        <circle
          cx={50}
          cy={50}
          r={radii[epoch]}
          fill="#fbbf24"
          fillOpacity={opacities[epoch]}
        />
      );
    }
    // Detector artifact appears only in epoch 0 so beginners immediately see it before it vanishes
    if (epoch === 0) {
      return <circle cx={62} cy={38} r={4.5} fill="#fb7185" />;
    }
    return null;
  }

  return (
    <section
      aria-labelledby="practice-heading"
      className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 id="practice-heading" className="text-xl font-semibold text-white">
            {t("title")}
          </h2>
          <p className="mt-1 text-sm text-slate-300">{t("subtitle")}</p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setPlaying((p) => !p)}
            aria-pressed={playing}
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-950 px-3.5 py-2 text-xs font-semibold text-white hover:border-sky-400"
          >
            {playing ? (
              <Pause className="h-3.5 w-3.5 text-amber-400" aria-hidden="true" />
            ) : (
              <Play className="h-3.5 w-3.5 text-sky-400" aria-hidden="true" />
            )}
            <span>{playing ? t("pause") : t("play")}</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setPlaying(false);
              setEpoch((e) => (e + 1) % EPOCHS.length);
            }}
            className="inline-flex items-center gap-1.5 rounded-xl bg-sky-500 px-3.5 py-2 text-xs font-semibold text-slate-950 hover:bg-sky-400"
          >
            <SkipForward className="h-3.5 w-3.5" aria-hidden="true" />
            <span>
              {t("nextFrame")} ({t("frameLabel")} {epoch + 1}/4)
            </span>
          </button>
        </div>
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-3">
        {CASES.map((item) => {
          const picked = selected[item.id];
          const isCorrect = picked === item.answer;

          return (
            <div
              key={item.id}
              className="flex flex-col justify-between rounded-xl border border-slate-800 bg-slate-950/90 p-4"
            >
              <div>
                <div className="flex items-center justify-between gap-2">
                  <h3 className="text-sm font-semibold text-white">
                    {t(`cases.${item.id}.title`)}
                  </h3>
                  <button
                    type="button"
                    onClick={() => {
                      setPlaying(false);
                      setEpoch((e) => (e + 1) % EPOCHS.length);
                    }}
                    className="inline-flex shrink-0 items-center gap-1 rounded-md border border-slate-700 bg-slate-900 px-2 py-0.5 font-mono text-[11px] text-sky-600 hover:border-sky-400"
                    title={t("nextFrame")}
                  >
                    <span>
                      {t("frameLabel")} {epoch + 1}/4
                    </span>
                    <SkipForward className="h-3 w-3" aria-hidden="true" />
                  </button>
                </div>

                <div className="mt-3 overflow-hidden rounded-lg border border-slate-800 bg-black">
                  <svg
                    viewBox="0 0 100 100"
                    className="h-36 w-full"
                    role="img"
                    aria-label={t(`cases.${item.id}.title`)}
                  >
                    {/* Fixed background reference stars */}
                    <circle cx={18} cy={22} r={2} fill="#94a3b8" />
                    <circle cx={82} cy={76} r={2.2} fill="#94a3b8" />
                    <circle cx={22} cy={78} r={1.6} fill="#94a3b8" />
                    {renderSimulatedDot(item.id)}
                  </svg>
                </div>

                <div className="mt-3 flex flex-wrap gap-1.5">
                  {(["motion", "variable", "artifact"] as Choice[]).map((choice) => (
                    <button
                      key={choice}
                      type="button"
                      onClick={() =>
                        setSelected((prev) => ({ ...prev, [item.id]: choice }))
                      }
                      aria-pressed={picked === choice}
                      className={`rounded-lg border px-2.5 py-1 text-xs font-medium transition-colors ${
                        picked === choice
                          ? choice === item.answer
                            ? "border-emerald-500 bg-emerald-500/20 text-emerald-300"
                            : "border-rose-500 bg-rose-500/20 text-rose-300"
                          : "border-slate-700 bg-slate-900 text-slate-300 hover:border-slate-500"
                      }`}
                    >
                      {t(`choices.${choice}`)}
                    </button>
                  ))}
                </div>
              </div>

              {picked && (
                <div
                  aria-live="polite"
                  className="mt-3 rounded-lg border border-slate-800 bg-slate-900/70 p-2.5 text-xs"
                >
                  {isCorrect ? (
                    <div className="space-y-1 text-emerald-300">
                      <p className="inline-flex items-center gap-1 font-semibold">
                        <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                        <span>{t("correct")}</span>
                      </p>
                      <p className="text-slate-300">
                        {t(`cases.${item.id}.explanation`)}
                      </p>
                    </div>
                  ) : (
                    <p className="inline-flex items-center gap-1 text-rose-300">
                      <HelpCircle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                      <span>{t("tryAgain")}</span>
                    </p>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { useTranslations } from "next-intl";
import { Flag, X } from "lucide-react";
import {
  saveMyFinding,
  submitFinding,
  type FindingItem,
} from "@/lib/api/platform";

type ReportFindingButtonProps = {
  defaultRa?: number;
  defaultDec?: number;
  onCreated?: (item: FindingItem) => void;
};

/**
 * "I found something!" button & modal form (#3).
 * Ready for #1's ViewerLayout `toolbarExtra` slot and usable standalone on /findings.
 */
export function ReportFindingButton({
  defaultRa,
  defaultDec,
  onCreated,
}: ReportFindingButtonProps) {
  const t = useTranslations("findings");
  const tErrors = useTranslations("errors");

  const initialRa = defaultRa !== undefined ? String(defaultRa) : "";
  const initialDec = defaultDec !== undefined ? String(defaultDec) : "";

  const [open, setOpen] = useState(false);
  const [ra, setRa] = useState(initialRa);
  const [dec, setDec] = useState(initialDec);
  const [note, setNote] = useState("");
  const [nickname, setNickname] = useState("");
  const [website, setWebsite] = useState(""); // honeypot
  const [submitting, setSubmitting] = useState(false);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const triggerRef = useRef<HTMLButtonElement>(null);
  const modalRef = useRef<HTMLDivElement>(null);
  const noteRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!open) return;
    noteRef.current?.focus();
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setOpen(false);
        window.setTimeout(() => triggerRef.current?.focus(), 0);
        return;
      }
      if (e.key === "Tab" && modalRef.current) {
        const focusable = Array.from(
          modalRef.current.querySelectorAll<HTMLElement>(
            'button:not([disabled]), [href], input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
          )
        ).filter((el) => el.offsetParent !== null);
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open]);

  function closeModal() {
    setOpen(false);
    window.setTimeout(() => triggerRef.current?.focus(), 0);
  }

  function openModal() {
    setRa(defaultRa !== undefined ? String(defaultRa) : "");
    setDec(defaultDec !== undefined ? String(defaultDec) : "");
    setErrorCode(null);
    setSuccess(false);
    setOpen(true);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!note.trim()) return;
    const raNum = Number(ra);
    const decNum = Number(dec);
    if (!ra.trim() || !dec.trim() || !Number.isFinite(raNum) || !Number.isFinite(decNum)) {
      setErrorCode("validation_error");
      return;
    }

    setSubmitting(true);
    setErrorCode(null);
    try {
      const created = await submitFinding({
        ra: raNum,
        dec: decNum,
        note: note.trim(),
        nickname: nickname.trim() || undefined,
        website,
      });
      saveMyFinding(created);
      onCreated?.(created);
      setSuccess(true);
      setNote("");
    } catch (err) {
      const code = err instanceof Error ? err.message : "unknown";
      setErrorCode(code);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        onClick={openModal}
        className="inline-flex items-center gap-1.5 rounded-lg bg-amber-300 px-3 py-1.5 text-xs font-semibold text-slate-100 transition-colors hover:bg-amber-300 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-300"
      >
        <Flag className="h-3.5 w-3.5" aria-hidden="true" />
        <span>{t("reportButton")}</span>
      </button>

      {open && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="finding-modal-title"
          onClick={(e) => {
            if (e.target === e.currentTarget) closeModal();
          }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/75 p-4 backdrop-blur-sm"
        >
          <div
            ref={modalRef}
            className="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl"
          >
            <div className="flex items-center justify-between gap-3">
              <h2 id="finding-modal-title" className="text-lg font-semibold text-white">
                {t("form.title")}
              </h2>
              <button
                type="button"
                onClick={closeModal}
                aria-label={t("form.close")}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>

            {success ? (
              <div className="mt-4 space-y-4">
                <p className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-300">
                  {t("form.success")}
                </p>
                <button
                  type="button"
                  onClick={closeModal}
                  className="w-full rounded-xl bg-sky-500 py-2 text-sm font-semibold text-slate-950 hover:bg-sky-400"
                >
                  {t("form.close")}
                </button>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="mt-4 space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label
                      htmlFor="finding-ra"
                      className="block text-xs font-medium text-slate-300"
                    >
                      {t("form.raLabel")}
                    </label>
                    <input
                      id="finding-ra"
                      type="number"
                      step="any"
                      min={0}
                      max={360}
                      required
                      value={ra}
                      onChange={(e) => setRa(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm text-white focus:border-sky-400 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label
                      htmlFor="finding-dec"
                      className="block text-xs font-medium text-slate-300"
                    >
                      {t("form.decLabel")}
                    </label>
                    <input
                      id="finding-dec"
                      type="number"
                      step="any"
                      min={-90}
                      max={90}
                      required
                      value={dec}
                      onChange={(e) => setDec(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm text-white focus:border-sky-400 focus:outline-none"
                    />
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between text-xs font-medium text-slate-300">
                    <label htmlFor="finding-note">{t("form.noteLabel")}</label>
                    <span className="font-mono text-slate-400">{note.length}/500</span>
                  </div>
                  <textarea
                    ref={noteRef}
                    id="finding-note"
                    required
                    maxLength={500}
                    rows={3}
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder={t("form.notePlaceholder")}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder:text-slate-400 focus:border-sky-400 focus:outline-none"
                  />
                </div>

                <div>
                  <label
                    htmlFor="finding-nickname"
                    className="block text-xs font-medium text-slate-300"
                  >
                    {t("form.nicknameLabel")}
                  </label>
                  <input
                    id="finding-nickname"
                    type="text"
                    maxLength={80}
                    value={nickname}
                    onChange={(e) => setNickname(e.target.value)}
                    placeholder={t("form.nicknamePlaceholder")}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder:text-slate-400 focus:border-sky-400 focus:outline-none"
                  />
                </div>

                {/* Honeypot anti-spam field */}
                <div className="hidden" aria-hidden="true">
                  <label htmlFor="finding-website">Website</label>
                  <input
                    id="finding-website"
                    type="text"
                    tabIndex={-1}
                    autoComplete="off"
                    value={website}
                    onChange={(e) => setWebsite(e.target.value)}
                  />
                </div>

                {errorCode && (
                  <p role="alert" className="text-xs text-rose-400">
                    {tErrors.has(errorCode) ? tErrors(errorCode) : tErrors("unknown")}
                  </p>
                )}

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={closeModal}
                    className="rounded-lg border border-slate-700 px-4 py-2 text-xs font-medium text-slate-300 hover:border-slate-500"
                  >
                    {t("form.cancel")}
                  </button>
                  <button
                    type="submit"
                    disabled={submitting || !note.trim()}
                    className="rounded-lg bg-amber-300 px-4 py-2 text-xs font-semibold text-slate-100 hover:bg-amber-300 disabled:opacity-50"
                  >
                    {submitting ? t("form.submitting") : t("form.submit")}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </>
  );
}

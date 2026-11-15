import { useTranslations } from "next-intl";

export function Footer() {
  const t = useTranslations("common.footer");

  return (
    <footer className="border-t border-slate-800/80 bg-slate-950 py-6 text-center text-xs text-slate-400">
      <div className="mx-auto max-w-6xl px-4">{t("credit")}</div>
    </footer>
  );
}

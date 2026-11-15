import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";

export default function LocaleNotFoundPage() {
  const t = useTranslations("common.notFound");

  return (
    <div className="mx-auto flex max-w-xl flex-col items-center justify-center px-4 py-24 text-center">
      <p className="font-mono text-sm font-semibold text-sky-400">404</p>
      <h1 className="mt-2 text-2xl font-bold text-white">{t("title")}</h1>
      <p className="mt-2 text-sm text-slate-300">{t("body")}</p>
      <Link
        href="/"
        className="mt-6 rounded-xl bg-sky-500 px-5 py-2.5 text-sm font-semibold text-slate-950 hover:bg-sky-400"
      >
        {t("backHome")}
      </Link>
    </div>
  );
}

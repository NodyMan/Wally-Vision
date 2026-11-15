"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { Link, usePathname, useRouter } from "@/i18n/navigation";
import { routing, type Locale } from "@/i18n/routing";
import { SimpleModeToggle } from "@/features/settings/SimpleModeToggle";
import { Telescope } from "lucide-react";

const LOCALE_LABELS: Record<Locale, string> = {
  en: "EN",
  ru: "RU",
  uz: "UZ",
};

function LocaleSwitcher({ locale, label }: { locale: Locale; label: string }) {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();

  function handleLocaleChange(nextLocale: Locale) {
    const qs = searchParams.toString();
    const target = qs ? `${pathname}?${qs}` : pathname;
    router.replace(target, { locale: nextLocale });
  }

  return (
    <div
      role="group"
      aria-label={label}
      className="inline-flex rounded-full border border-slate-700 bg-slate-900/80 p-0.5"
    >
      {routing.locales.map((loc) => {
        const active = loc === locale;
        return (
          <button
            key={loc}
            type="button"
            onClick={() => handleLocaleChange(loc)}
            aria-pressed={active}
            className={`rounded-full px-2 py-1 text-xs font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-sky-400 sm:px-2.5 ${
              active
                ? "bg-sky-500 text-slate-950"
                : "text-slate-300 hover:text-white"
            }`}
          >
            {LOCALE_LABELS[loc]}
          </button>
        );
      })}
    </div>
  );
}

function LocaleSwitcherFallback({ locale, label }: { locale: Locale; label: string }) {
  return (
    <div
      role="group"
      aria-label={label}
      className="inline-flex rounded-full border border-slate-700 bg-slate-900/80 p-0.5"
    >
      {routing.locales.map((loc) => (
        <span
          key={loc}
          className={`rounded-full px-2 py-1 text-xs font-medium sm:px-2.5 ${
            loc === locale ? "bg-sky-500 text-slate-950" : "text-slate-300"
          }`}
        >
          {LOCALE_LABELS[loc]}
        </span>
      ))}
    </div>
  );
}

export function Header() {
  const t = useTranslations("common");
  const locale = useLocale() as Locale;
  const pathname = usePathname();

  const navLinks = [
    { href: "/", label: t("nav.home") },
    { href: "/view", label: t("nav.viewer") },
    { href: "/findings", label: t("nav.findings") },
    { href: "/about", label: t("nav.about") },
  ] as const;

  return (
    <header className="sticky top-0 z-40 border-b border-slate-800 bg-slate-900/85 backdrop-blur">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-3 focus:z-50 focus:rounded-lg focus:bg-sky-500 focus:px-3 focus:py-2 focus:text-xs focus:font-semibold focus:text-slate-950"
      >
        {t("skipToContent")}
      </a>

      <div className="mx-auto flex max-w-6xl items-center justify-between gap-2 px-4 py-3">
        <div className="flex items-center gap-6">
          <Link
            href="/"
            className="flex items-center gap-2 text-lg font-semibold tracking-tight text-white hover:text-sky-400 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-400"
          >
            <Telescope className="h-5 w-5 text-sky-400" aria-hidden="true" />
            <span>{t("appName")}</span>
          </Link>

          <nav aria-label="Main navigation" className="hidden items-center gap-1 text-sm sm:flex">
            {navLinks.map((item) => {
              const active =
                item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={`rounded-md px-2 py-1 transition-colors focus-visible:outline-2 focus-visible:outline-sky-400 ${
                    active ? "bg-slate-800 text-white" : "text-slate-300 hover:text-white"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="flex items-center gap-2">
          <SimpleModeToggle />

          <Suspense fallback={<LocaleSwitcherFallback locale={locale} label={t("language.label")} />}>
            <LocaleSwitcher locale={locale} label={t("language.label")} />
          </Suspense>
        </div>
      </div>

      {/* Compact mobile navigation bar (375px+) */}
      <nav
        aria-label="Mobile navigation"
        className="flex items-center justify-around border-t border-slate-800/80 px-2 py-1.5 text-xs sm:hidden"
      >
        {navLinks.map((item) => {
          const active =
            item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={`whitespace-nowrap rounded-lg px-2.5 py-1.5 font-medium transition-colors ${
                active ? "bg-slate-800 text-white" : "text-slate-300 hover:text-white"
              }`}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}

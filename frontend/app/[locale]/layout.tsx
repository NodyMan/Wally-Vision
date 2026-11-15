import type { Metadata } from "next";
import { JetBrains_Mono, Manrope } from "next/font/google";
import { notFound } from "next/navigation";
import { NextIntlClientProvider, hasLocale } from "next-intl";
import { getMessages, setRequestLocale } from "next-intl/server";
import { routing } from "@/i18n/routing";
import { LayoutShell } from "@/features/home/LayoutShell";
import "../globals.css";

// Display type and readout type; both cover Latin and Cyrillic (en, uz, ru).
const display = Manrope({ subsets: ["latin", "latin-ext", "cyrillic"], variable: "--font-display", display: "swap" });
const readout = JetBrains_Mono({ subsets: ["latin", "latin-ext", "cyrillic"], variable: "--font-readout", display: "swap" });

export const metadata: Metadata = {
  title: "SkyBlink — SPHEREx Blink & Motion Explorer",
  description:
    "Explore NASA SPHEREx infrared sky epochs as blink animations and spot moving objects, brown dwarfs and variable stars.",
};

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) {
    notFound();
  }

  setRequestLocale(locale);
  const messages = await getMessages();

  return (
    <html lang={locale} className={`h-full antialiased ${display.variable} ${readout.variable}`}>
      <body className="flex min-h-full flex-col text-slate-100">
        <NextIntlClientProvider messages={messages}>
          <LayoutShell>{children}</LayoutShell>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}

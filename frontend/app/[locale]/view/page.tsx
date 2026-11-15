// /view?ra=&dec=&name=&fov=&mode=&det=&t=   The viewer with all layers (owner #1); logic is in features/viewer.
// Developed with SI assistance (Claude); reviewed by team #1.
import { Suspense } from "react";
import { setRequestLocale } from "next-intl/server";
import { SkyBlinkView } from "@/features/viewer/SkyBlinkView";

export default async function ViewPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);

  return (
    <Suspense fallback={<div className="min-h-[60dvh]" />}>
      <SkyBlinkView />
    </Suspense>
  );
}

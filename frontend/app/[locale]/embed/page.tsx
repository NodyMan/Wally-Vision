import { Suspense } from "react";
import { setRequestLocale } from "next-intl/server";
import { EmbedClient } from "@/features/home/EmbedClient";

export default async function EmbedPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);

  return (
    <Suspense fallback={<div className="min-h-[380px] bg-slate-950" />}>
      <EmbedClient />
    </Suspense>
  );
}

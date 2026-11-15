import { setRequestLocale } from "next-intl/server";
import { HomeClient } from "@/features/home/HomeClient";
import type { PresetItem } from "@/lib/api/platform";
import presetsData from "@/lib/mocks/presets.json";

export default async function HomePage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);

  return <HomeClient initialPresets={presetsData as PresetItem[]} />;
}

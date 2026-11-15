import { setRequestLocale } from "next-intl/server";
import { FindingsClient } from "@/features/findings/FindingsClient";

export default async function FindingsPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);

  return <FindingsClient />;
}

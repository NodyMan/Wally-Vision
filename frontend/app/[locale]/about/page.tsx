import { getTranslations, setRequestLocale } from "next-intl/server";
import { PracticeSection } from "@/features/home/PracticeSection";

export default async function AboutPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("about");

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-8 px-4 py-10">
      <div>
        <h1 className="text-3xl font-bold text-white">{t("title")}</h1>
        <p className="mt-3 text-base text-slate-300">{t("intro")}</p>
      </div>

      <div className="grid gap-4">
        <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
          <h2 className="text-xl font-semibold text-sky-600">
            {t("sections.spherexTitle")}
          </h2>
          <p className="mt-2 text-sm leading-6 text-slate-300">
            {t("sections.spherexBody")}
          </p>
        </section>

        <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
          <h2 className="text-xl font-semibold text-sky-600">
            {t("sections.motionTitle")}
          </h2>
          <p className="mt-2 text-sm leading-6 text-slate-300">
            {t("sections.motionBody")}
          </p>
        </section>

        <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
          <h2 className="text-xl font-semibold text-sky-600">
            {t("sections.brownDwarfsTitle")}
          </h2>
          <p className="mt-2 text-sm leading-6 text-slate-300">
            {t("sections.brownDwarfsBody")}
          </p>
        </section>

        <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
          <h2 className="text-xl font-semibold text-sky-600">
            {t("sections.artifactsTitle")}
          </h2>
          <p className="mt-2 text-sm leading-6 text-slate-300">
            {t("sections.artifactsBody")}
          </p>
        </section>
      </div>

      <PracticeSection />

      <section>
        <h2 className="text-lg font-semibold text-white">{t("linksTitle")}</h2>
        <ul className="mt-3 flex flex-wrap gap-3 text-sm text-sky-400">
          <li>
            <a
              href="https://irsa.ipac.caltech.edu/Missions/spherex.html"
              target="_blank"
              rel="noreferrer"
              className="underline hover:text-sky-600"
            >
              NASA/IPAC IRSA SPHEREx
            </a>
          </li>
          <li>
            <a
              href="https://backyardworlds.org"
              target="_blank"
              rel="noreferrer"
              className="underline hover:text-sky-600"
            >
              Backyard Worlds: Planet 9
            </a>
          </li>
          <li>
            <a
              href="http://byw.tools/wiseview"
              target="_blank"
              rel="noreferrer"
              className="underline hover:text-sky-600"
            >
              WiseView
            </a>
          </li>
          <li>
            <a
              href="https://www.cosmos.esa.int/gaia"
              target="_blank"
              rel="noreferrer"
              className="underline hover:text-sky-600"
            >
              ESA Gaia DR3
            </a>
          </li>
          <li>
            <a
              href="https://catwise.github.io/"
              target="_blank"
              rel="noreferrer"
              className="underline hover:text-sky-600"
            >
              CatWISE2020
            </a>
          </li>
        </ul>
      </section>
    </div>
  );
}

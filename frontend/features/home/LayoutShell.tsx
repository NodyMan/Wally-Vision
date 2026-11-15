"use client";

import { usePathname } from "@/i18n/navigation";
import { Header } from "./Header";
import { Footer } from "./Footer";

export function LayoutShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isEmbed = pathname === "/embed" || pathname.startsWith("/embed/");

  if (isEmbed) {
    return (
      <main id="main-content" tabIndex={-1} className="min-h-screen bg-slate-950">
        {children}
      </main>
    );
  }

  return (
    <>
      <Header />
      <main id="main-content" tabIndex={-1} className="flex-1 focus:outline-none">
        {children}
      </main>
      <Footer />
    </>
  );
}

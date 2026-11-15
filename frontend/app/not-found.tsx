import Link from "next/link";
import "./globals.css";

export default function RootNotFoundPage() {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-slate-950 text-slate-100 antialiased">
        <main className="mx-auto flex max-w-xl flex-col items-center justify-center px-4 py-24 text-center">
          <p className="font-mono text-sm font-semibold text-sky-400">404</p>
          <h1 className="mt-2 text-2xl font-bold text-white">Page not found</h1>
          <p className="mt-2 text-sm text-slate-300">
            The requested SkyBlink page does not exist.
          </p>
          <Link
            href="/en"
            className="mt-6 rounded-xl bg-sky-500 px-5 py-2.5 text-sm font-semibold text-slate-950 hover:bg-sky-400"
          >
            Back to SkyBlink
          </Link>
        </main>
      </body>
    </html>
  );
}

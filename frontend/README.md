# SkyBlink frontend

Next.js 16 + React 19 + Tailwind 4 + next-intl (en/ru/uz) + zustand + Aladin Lite.
Project overview, results on real SPHEREx data and data sources: see the [root README](../README.md).

Live site: https://frontend-three-xi-80.vercel.app

```bash
npm ci
npm run dev        # http://localhost:3000, needs the backend on :8000 (or set NEXT_PUBLIC_API_URL)
npm test && npx tsc --noEmit && npm run lint
```

Without a reachable backend the site answers the five featured fields from its own demo API (`app/api/[...path]`).

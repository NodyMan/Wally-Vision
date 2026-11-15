# SkyBlink Deployment & Pre-Submission Checklist

## 1. GitHub Setup
```bash
cd D:\skyblink
git remote add origin https://github.com/<your-org>/skyblink.git
git push -u origin main
```
- Enable branch protection on `main` (require PR + green GitHub Actions CI).
- Teammates branch as `p1/*` (#1) and `p2/*` (#2).

## 2. Backend Deploy (Render)
Use the root [render.yaml](../render.yaml) Blueprint (with `rootDir: backend`, or connect `backend/` manually):
- **Root Directory:** `backend`
- **Build Command:** `pip install -r requirements.txt && python manage.py collectstatic --noinput`
- **Start Command:** `python manage.py migrate --noinput && gunicorn skyblink.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 120`
- **Persistent Disk:** mounted at `/var/data` (`CACHE_DIR=/var/data/cache`, `DATABASE_URL=sqlite:////var/data/db.sqlite3` or Render Postgres)
- **Environment Variables:**
  - `DEBUG=False`
  - `SECRET_KEY=<random-strong-secret>`
  - `ALLOWED_HOSTS=<your-service>.onrender.com`
  - `CORS_ALLOWED_ORIGINS=https://<your-app>.vercel.app,http://localhost:3000`
  - `CSRF_TRUSTED_ORIGINS=https://<your-app>.vercel.app,https://<your-service>.onrender.com`
  - `NUM_PROXIES=1`
  - `SKYBLINK_MAX_JOBS=1` — one IRSA download job at a time (a cold field takes minutes)
  - `SKYBLINK_ALLOW_COLD=0` — emergency switch: serve only the 5 cached presets and cached results;
    other coordinates get a clear "demo server" message instead of a 502. Keep `1` while it copes.
- Run ONE gunicorn process (`--workers 1 --threads 8`): download jobs live in memory.
- Verify `https://<your-service>.onrender.com/api/health` returns `{"status": "ok"}`.

## 3. Frontend Deploy (Vercel)
- **Root Directory:** `frontend`
- **Environment Variable:** `NEXT_PUBLIC_API_URL=https://<your-service>.onrender.com`
- Verify `https://<your-app>.vercel.app` shows the green **"Backend online"** status badge on the home page.

## 4. Pre-Submission Checklist (H42–H46)
- [ ] `#1` and `#2` merged to `main`, `backend/scripts/prefetch.py` warmed cache for all 5 presets
- [ ] All 5 benchmark targets load in `< 3s` in incognito mode (desktop & 375 px mobile)
- [ ] Search tested with object name + 3 coordinate formats (`hms/dms`, decimal, colon)
- [ ] `en`, `ru`, `uz` switched cleanly with zero missing keys (`node scripts/check_i18n.mjs`)
- [ ] `/embed`, `/findings`, and `/about` (3-case trainer) verified live
- [ ] Lighthouse Accessibility score ≥ 90
- [ ] Demo video recorded, `README.md` updated with live URLs & GIF, submitted before H46
- [ ] No secrets (`.env`, API tokens) committed in git history

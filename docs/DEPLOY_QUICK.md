# Деплой SkyBlink за 20 минут (15.11, для сдачи)

Проверено локально 15.11: `next build` проходит, `manage.py check --deploy` и `collectstatic` проходят.
5 пресетов лежат в `backend/viewer/static_cache/` и открываются без обращения к IRSA.

## 0. GitHub (2 мин)
1. На github.com: **New repository** → имя `skyblink` → **Public** → без README.
2. В папке `hackathon`:
   ```
   git remote add origin https://github.com/<ваш-логин>/skyblink.git
   git push -u origin main
   ```

## 1. Бэкенд на Render (10 мин)
1. render.com → **New** → **Blueprint** → выбрать репозиторий `skyblink`. Render прочитает `render.yaml`.
2. План в `render.yaml` — **starter** (платный, с диском 5 ГБ для кэша и базы находок).
   Без оплаты: в настройках сервиса выбрать **Free** и удалить диск. Тогда после каждого перезапуска
   пропадут находки и кэш новых полей, но 5 пресетов работают всегда (они в репозитории).
3. Переменные, которые надо вписать руками (остальные уже в `render.yaml`):
   - `CORS_ALLOWED_ORIGINS` = `https://<ваш-проект>.vercel.app`
   - `CSRF_TRUSTED_ORIGINS` = `https://<ваш-проект>.vercel.app,https://<сервис>.onrender.com`
   - для Free без диска: `CACHE_DIR` = `/tmp/skyblink-cache`, `DATABASE_URL` = `sqlite:////tmp/db.sqlite3`
4. Проверка: `https://<сервис>.onrender.com/api/health` → `{"status": "ok"}`,
   `https://<сервис>.onrender.com/api/presets` → 5 объектов.
5. Если сервер не справляется с загрузками из IRSA во время показа: `SKYBLINK_ALLOW_COLD` = `0`
   (останутся только готовые поля, вместо 502 будет понятное сообщение).

## 1b. Бэкенд на Hugging Face вместо Render (бесплатно, без карты)
Проверено локально 15.11 с теми же переменными, что в `deploy/huggingface/Dockerfile`, и с пустым кэшем:
5 пресетов, кадры, кривые блеска и спектры отвечают из репозитория без обращения к IRSA.
1. Space уже создан: `huggingface.co/spaces/bymakhmud/SkyBlink` (SDK **Docker**, **CPU basic** — бесплатно).
2. Space → **Settings** → **Variables and secrets** → **New secret**: `SECRET_KEY` = любая длинная случайная строка.
   (Без него контейнер сам сделает случайный ключ при каждом старте — для API это не страшно.)
3. В Git Bash из папки `hackathon`:
   ```
   bash deploy/huggingface/build_space.sh
   cd /c/skyblink_deploy/hf-space && git push
   ```
   Скрипт кладёт PNG в git-lfs: без этого Hugging Face отклоняет push («contains binary files»).
   Логин при push: имя `bymakhmud`, пароль — **токен с правом write** с huggingface.co/settings/tokens.
4. Сборка 5–10 минут (вкладка **Logs** у Space). Проверка: `https://bymakhmud-skyblink.hf.space/api/health`.
5. На Vercel: `NEXT_PUBLIC_API_URL` = `https://bymakhmud-skyblink.hf.space` (именно `*.hf.space`, не адрес
   страницы huggingface.co). CORS для `*.vercel.app` уже разрешён в `settings.py`, ничего вписывать не надо.
6. Space засыпает после 48 ч без запросов; просыпается за 1–2 минуты (сайт сам повторяет запросы 90 с).

## 2. Фронтенд на Vercel (5 мин)
1. vercel.com → **Add New** → **Project** → репозиторий `skyblink`.
2. **Root Directory**: `frontend`. Framework определится сам (Next.js).
3. Переменная окружения: `NEXT_PUBLIC_API_URL` = `https://<сервис>.onrender.com` (без `/` в конце).
4. **Deploy**. Затем вписать адрес Vercel в `CORS_ALLOWED_ORIGINS` на Render (шаг 1.3) и перезапустить бэкенд.

## 3. Проверка перед сдачей (3 мин, в режиме инкогнито)
- Главная: 5 карточек с картинками, поиск «barnard» открывает просмотр.
- `/en/view?ra=331.04383&dec=-56.78269&fov=300&mode=diff&det=6&name=Epsilon%20Indi%20B` —
  плитка «Измеренный сдвиг» 6.0″, кольца на снимке.
- Переключение EN / RU / UZ, телефон.
- Бесплатный Render засыпает: первый запрос после паузы идёт ~1 минуту. Откройте сайт за 2 минуты до показа.

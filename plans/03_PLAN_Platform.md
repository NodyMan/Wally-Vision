# План участника #3: Platform & People (full-stack)

> **Редакция 1 — 14 ноября 2026.** Все интерфейсы и JSON-схемы сверять с `00_COMMON.md` (единственный источник правды; **сначала прочитать его §0** и §10 — таймлайн под реальный дедлайн). Требования к подаче — `docs/PITCH.md`.

> **Агенту:** ты делаешь фундамент и всё, что видит обычный человек до и вокруг плеера: каркас Django и Next.js, деплой, поиск, пресеты, i18n (en/ru/uz), онбординг, Простой режим, About, находки, доступность — и **подачу на конкурс**. Плеер (#1) и научные слои (#2) встраиваются в твой каркас. В их папки не пиши. Главная ценность проекта — **простота для человека без знаний астрономии**: каждый экран должен быть понятен за 5 секунд. Validity в судействе прямо включает «usable and user-friendly» — это твой вклад в баллы.

## Backend: что твоё
`backend/skyblink/` (settings, root urls) · `backend/platform_api/` (`/api/health`, `/api/resolve`, `/api/presets`) · `backend/findings/` · `requirements.txt`, `render.yaml`/`railway.json`, `Procfile` · `shared/presets.json` (тексты; координаты, fov, mode и detector подбирает #1).

## Frontend: что твоё
`app/[locale]/layout.tsx`, `page.tsx`, `about/`, `findings/`, `embed/` · `features/home/`, `findings/`, `onboarding/`, `settings/` · `lib/api/platform.ts` · `i18n/request.ts` · `messages/*/{common,home,onboarding,about,findings,errors,presets}.json` · `scripts/check_i18n.mjs` · README.

---

## сб 14:00–15:00. Организационное (до кода!)
- [ ] Написать **Local Lead**: точное время окончания нашего Local Event. Если раньше вс 23:59 — сразу сказать всем и сдвинуть §10 COMMON.
- [ ] Проверить вкладку **Members** на странице команды: все зарегистрированы, один Local Event, никто не в waitlist.
- [ ] Создать **публичный** репозиторий GitHub `skyblink`, ветки по COMMON §9, `.gitignore` (`.env`, `node_modules`, `__pycache__`, `research/*/cache`, `research/*/out`, `*.fits`).
- [ ] Положить в репозиторий `plans/`, `docs/`, `research/core/` из архива.

## сб 14:00–17:00. Каркасы + деплой hello-world (до Sync 1)
**Backend (Django + DRF):**
- `django-admin startproject skyblink backend` → apps `platform_api`, `findings` (+ пустые `core`, `viewer`, `science` для #1/#2, чтобы `urls.py` сразу имел `include` каждого).
- `django-cors-headers` (allowlist: домен Vercel + `http://localhost:3000`, без `*`), `whitenoise`, `dj-database-url` (SQLite локально).
- `/api/health` → `{"status":"ok"}`.
- **gunicorn timeout ≥ 120 с** и 2 воркера (тяжёлые запросы идут фоново, COMMON §6, но процесс не должен убиваться на холодном старте).
- Деплой: **Railway** (не засыпает — лучше для судейства) или Render. `CACHE_DIR` через переменную окружения.

**Frontend (Next.js App Router + TS + Tailwind):**
- `next-intl` с локалями `en` (по умолчанию), `uz` (латиница), `ru`; переключатель языка в шапке; namespaces по COMMON §7, файлы `messages/{en,ru,uz}/<ns>.json`.
- `NEXT_PUBLIC_API_URL`; `lib/api/platform.ts` с `getHealth()`.
- Деплой на Vercel. Главная показывает «Backend: OK».

**Sync 1 (сб 17:00):** две живые ссылки, фронт видит бэкенд.

## сб 17:00–22:00. Поиск, пресеты, главная
- BE `/api/resolve?q=`: 
  1) алиасы пресетов (`wise 0855`, `barnard`, `eps ind b`, `rw aur`, `r dra`) → координаты из `shared/presets.json`;
  2) координаты в форматах `08h55m10.8s -07d14m42s`, `133.795 -7.245`, `08:55:10.8 -07:14:42` (`astropy.coordinates.SkyCoord`, валидация RA [0,360), Dec [-90,90], отказ на NaN);
  3) иначе Sesame/SIMBAD (`SkyCoord.from_name`, таймаут 10 с, кэш). Ответ `{ra, dec, name, source}`; ошибка `not_found` / `invalid_coordinates`.
- BE `/api/presets` → `shared/presets.json`. Заполнить тексты `title/short/what_you_see` на en/ru/uz для 5 объектов простым языком:
  - WISE 0855 — «самый холодный известный коричневый карлик, почти планета; быстро ползёт по небу»;
  - Barnard's Star — «звезда с самым быстрым видимым движением»;
  - ε Ind B — «пара коричневых карликов рядом со звездой»;
  - RW Aur, R Dra — «переменные звёзды: не двигаются, а меняют яркость» (R Dra — мирида).
- FE главная (`features/home`): крупное поле «Enter a star name or coordinates», 5 карточек-пресетов (картинка = первый кадр из кэша #1, одна строка описания), кнопка «How does it work?». Поиск → `/view?ra=&dec=&name=`.
- Пинг `/api/health` при загрузке главной (разбудить бэкенд).

**Sync 2 (сб 22:00):** главная и поиск работают на проде.

## вс 08:00–12:00. Онбординг, Простой режим, About, ошибки
- `features/onboarding`: тур из 4 шагов при первом визите (localStorage, кнопка «пропустить»): что ты видишь → как работает blink → как заметить движение (пара «белое+чёрное») → как отметить находку.
- `features/settings`: переключатель **Simple / Expert** → `store.simpleMode` (поле добавить в `lib/store.ts` через PR к #1). По умолчанию Simple.
- Вкладка **«What am I seeing?»** в `bottomTabs`: текст `what_you_see` пресета или общий текст по режиму (frames/diff/sum).
- `errors.*` на 3 языках для всех кодов COMMON §6, включая `wavelength_mismatch` и `few_epochs` — человеческим языком («Для этого места неба пока мало снимков SPHEREx»).
- `/about`: что такое SPHEREx, blink, LVF простыми словами, ограничения, ссылки на данные NASA, раздел «Use of AI (SI)».
- `/embed?ra&dec&det`: плеер #1 без тулбара + кнопка «Copy iframe code» (компонент берёшь у #1).

**Sync 3 (вс 12:00, MVP):** 5 пресетов end-to-end на проде, на 3 языках.

## вс 12:00–16:00. Находки + доступность
- BE `findings`: модель `Finding(ra, dec, note, nickname?, created_at, ip_hash)`, POST/GET `/api/findings`, rate-limit по IP (например, 5 в час), honeypot-поле `website`, длина `note` ≤ 500. Без аккаунтов.
- FE кнопка «I found something!» в `toolbarExtra` → форма с подставленными координатами → страница `/findings`. Текст: «Your note is a candidate for experts to check — not a confirmed discovery».
- Доступность: контраст AA, `aria-label` на всех кнопках, работа с клавиатуры, `prefers-reduced-motion`, ничего не передаётся только цветом. Lighthouse Accessibility ≥ 90.
- `scripts/check_i18n.mjs` в CI: нет пропущенных ключей en/ru/uz. Вычитать ru и uz у всех.

## вс 16:00–21:30. ПОДАЧА (с 16:00 — главная задача; код только мелкие баги)
По `docs/PITCH.md`:
- [ ] 16:00–18:00: собрать у #1/#2 лучшие GIF и скриншоты; записать скринкаст по сценарию §2.
- [ ] 18:00–20:00: монтаж ≤ 30 с, **английские субтитры**, загрузка на YouTube (Unlisted/Public), проверка в инкогнито.
- [ ] Заполнить форму: Project Name, Summary, Demo link, Final Project link, Detailed Description (+ таблица соответствия §4), NASA Data, References, SI.
- [ ] README: что это, ссылки, как запустить, NASA-данные, раздел «Use of AI (SI)», лицензия.
- [ ] Финальная проверка с телефона: сайт, все 5 пресетов, переключение языков.
- [ ] **21:30 — «Submit for Judging»** (обе галочки). Скриншот подтверждения в чат команды.

## Чек-лист
- [ ] Local Lead ответил про время дедлайна; Members tab в порядке
- [ ] Публичный GitHub, сайт на Vercel, бэкенд на Railway/Render — открываются в инкогнито
- [ ] Поиск: имена, 3 формата координат, понятные ошибки
- [ ] Онбординг, Simple/Expert, «What am I seeing?», About
- [ ] en/ru/uz без пропусков; Lighthouse Accessibility ≥ 90; мобильная версия 375 px
- [ ] Видео ≤ 30 с с EN-субтитрами; форма полностью на английском; подано до 21:30

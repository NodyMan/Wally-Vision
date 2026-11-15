# План участника #2: Science Layers (full-stack)

> **Редакция 1 — 14 ноября 2026.** Все интерфейсы и JSON-схемы сверять с `00_COMMON.md` (единственный источник правды; **сначала прочитать его §0** — проверенные факты, и §13 — научные правила). Факты о данных — `docs/DATA_NOTES.md`.

> **Агенту:** ты делаешь научные слои поверх плеера #1 — насквозь, от Django до Next.js: каталоги со стрелками движения, спектр, кривую блеска, Aladin-панель, сравнение с WISE. Встраиваешься в слоты `ViewerLayout` (#1): `overlay`, `toolbarExtra`, `sidePanel`, `bottomTabs`. Общую библиотеку `backend/core` (#1) используешь, но **не правишь** — нужна функция → PR или просьба к #1. В чужие папки не пиши. Команда не астрономы: объясняй астрономию в комментариях и в UI простыми словами. Каждый научный вывод в UI помечай честно: «preview», «кандидат, требующий проверки».

## Backend: что твоё
`backend/science/` (`/api/catalog`, `/api/spectrum`, `/api/lightcurve`, `/api/badpixels`, `/api/rgb`, бонус `/api/asteroids`) · `research/science/` · функция прогрева в `backend/scripts/prefetch.py` · половина `docs/DATA_NOTES.md` (каталоги, FLAGS, спектры).
Зависимости: `astropy astroquery numpy` (+ `photutils` только если реально делаешь фотометрию и тестируешь её).

## Frontend: что твоё
`features/science/*` (CatalogOverlay, SpectrumChart, LightCurveChart, AladinPanel, WiseCompare, ScienceToolbar) · `lib/api/science.ts` · `messages/*/science.json`, `messages/*/features.json`.

## Главные научные правила (кратко из COMMON §13)
- Детекторы не смешивать. Кривая блеска — **один детектор и узкое окно длины волны** (LVF).
- PM переносить на дату каждого снимка: Gaia DR3 — эпоха 2016.0; у CatWISE2020 своя эпоха (⚠️ проверить в описании каталога).
- «Нет совпадения в Gaia» ≠ открытие. Текст в UI: **«candidate — needs verification»**.
- WISE 0855 и ε Ind B слишком тусклые в оптике и, скорее всего, **отсутствуют в Gaia** — это ожидаемо и хорошо для демо, но их движение надо брать из **CatWISE2020**.

---

## сб 14:00–17:00. Spike (до Sync 1)
`research/science/spike_catalogs.py`:
1. **Gaia DR3** через VizieR `I/355/gaiadr3` (`astroquery.vizier`, быстрее, чем асинхронные задания Gaia-архива): конус радиусом FOV/2 вокруг WISE 0855 и Barnard's Star. Колонки: `Source`, `RA_ICRS`, `DE_ICRS`, `pmRA` (это μα·cosδ, мас/год), `pmDE`, `Gmag`, `Plx`.
2. **CatWISE2020** через VizieR `II/365/catwise` (или IRSA TAP `catwise_2020`): те же точки. ⚠️ Записать в DATA_NOTES **единицы pmRA/pmDE и эпоху координат** — не угадывать.
3. Ответить на вопросы и записать в `DATA_NOTES.md`:
   - есть ли WISE 0855 и ε Ind B в CatWISE2020, их PM;
   - есть ли они в Gaia DR3 (ожидаем: нет).
4. **FLAGS**: выписать биты из **Table 16 SPHEREx Explanatory Supplement** и предложить маску («какие биты прячем на картинке») → `DATA_NOTES.md` + константа `FLAG_POLICY` для `core` (передать #1).
5. Черновой спектр: по вырезкам из `research/core/spike.py` (#1) взять для каждой вырезки поток в апертуре вокруг цели + `target_wavelength_um` → точечный график λ–поток. Если #1 ещё не готов — взять 5–10 вырезок вручную по SIA2 (см. DATA_NOTES §0).

**Sync 1:** показать таблицу Gaia/CatWISE с PM и черновой спектр WISE 0855.

## сб 17:00–22:00. `/api/catalog` + CatalogOverlay
- BE: `/api/catalog?ra&dec&fov&source=gaia|catwise` → источники в **той же сетке**, что `/api/blink` (`core.grid.make_grid` + `sky_to_pix`; 0-based PNG-пиксели, COMMON §6). Для каждого источника: `x, y` на эпоху сетки, `dx_per_yr, dy_per_yr` (в пикселях/год), `mag`, `pmra, pmdec`, `match_status` (`matched | no_confident_match`). В ответ — `catalog_release`, `reference_epoch`, `match_radius_arcsec`.
- Кэш ответов (ключ — округлённые ra/dec/fov/source). Таймаут к VizieR 20 с, при ошибке — `irsa_timeout`-подобный код `catalog_timeout` (согласовать с #1 в COMMON).
- FE `CatalogOverlay.tsx` в слот `overlay`: SVG-кружки + **стрелки PM** с длиной = сдвиг за `pmYears` (ползунок 1–20 лет в `toolbarExtra`). Источники с |PM| > 1″/год — выделить цветом **и** формой (не только цветом — доступность). Подсказка по наведению/тапу: имя, звёздная величина, «moves N″ per year».
- Кнопки в `toolbarExtra`: Gaia, CatWISE, «bad pixels». Всё видно и в Простом режиме, кроме ползунка лет.

## сб 22:00 – вс 12:00 (с перерывом на сон). Aladin + сравнение с WISE (обязательно, COMMON §0/§11)
- `AladinPanel.tsx` в слот `sidePanel` (на мобильных — отдельная вкладка): Aladin Lite v3 по CDN, центр = цель, FOV = FOV плеера. Слои: SPHEREx HiPS от IRSA (если найдётся ID — ⚠️ проверить в туториале «HiPS All-Sky Cube»), unWISE (`CDS/P/unWISE/color-W2-W1W2-W1` — ⚠️ проверить ID), 2MASS.
- `WiseCompare.tsx`: шторка «WISE ~2010 ↔ SPHEREx 2025–26» для пресетов коричневых карликов + ссылка «Open in WiseView». Это главный козырь для движения: сдвиг в SPHEREx 1–2 px, а за ~15 лет у WISE 0855 — порядка 2′.
- Прогрев: функция в `prefetch.py`, кэширующая `/api/catalog` для 5 пресетов.

**Sync 3 (вс 12:00):** стрелки Gaia/CatWISE и Aladin работают на проде для 5 пресетов.

## вс 12:00–16:00. Спектр и кривая блеска (preview)
- BE `/api/spectrum?ra&dec&source=spectral_images` (основной для MVP): по всем доступным вырезкам цели (через `core`) — апертурная сумма в радиусе ~2 px минус локальный фон (кольцо), `wavelength_um` из WCS-WAVE, `err` из VARIANCE. Для движущейся цели **сдвигать апертуру по дате снимка на PM** (CatWISE/Gaia). Ответ: `points`, `features` (H₂O ~3.0, CH₄ ~3.3, CO₂ ~4.27, CO ~4.67 мкм — ⚠️ сверить по литературе), `quality: "preview"`.
- `source=allsky_cube` — только если останется время (другой продукт, пиксель ~12.9″, каналы 51–52 пустые).
- BE `/api/lightcurve?ra&dec&detector` (+ окно длины волны): точки только одного детектора; если разброс λ в выборке больше допуска — `quality: "wavelength_mixed"` и предупреждение в UI. Проверить на R Dra (снимается непрерывно, много точек) и RW Aur.
- FE `SpectrumChart.tsx` (Recharts) во вкладке `bottomTabs` «Spectrum»: точки с ошибками, вертикальные линии молекул с подсказкой простым языком («Methane: seen in cold brown dwarfs»). Строится по `store.selected` (клик в плеере #1), по умолчанию — центр.
- FE `LightCurveChart.tsx` во вкладке «Light curve»: дата–поток, подпись детектора и длины волны, бейдж «Preview».

**Sync 4 (вс 16:00):** спектр WISE 0855 и кривая блеска R Dra на проде.

## вс 16:00–18:00. Бонусы — только если всё выше готово
- `/api/asteroids?ra&dec&fov&mjd` через `astroquery.imcce.Skybot.cone_search` → метки известных астероидов на дату кадра (чтобы люди не «открывали» известные).
- `/api/rgb` — ложные цвета из трёх детекторов. Первым в списке на выброс (COMMON §12).

## вс 18:00 — Feature freeze
Только баги (метка `p2`) + 2–3 скриншота/ролика стрелок и спектра для #3 (видео и страница проекта).

## Чек-лист
- [ ] DATA_NOTES: Gaia/CatWISE (единицы, эпохи), наличие WISE 0855/ε Ind B, таблица FLAGS и выбранная маска
- [ ] `/api/catalog` в той же сетке, что `/api/blink` (тест: Barnard попадает в центр ±1 px)
- [ ] Стрелки PM + бейдж «candidate — needs verification» (не «discovery»)
- [ ] Aladin + сравнение с WISE для пресетов коричневых карликов
- [ ] Спектр WISE 0855 и кривая блеска R Dra с пометкой «Preview»
- [ ] Всё работает на 375 px, доступно с клавиатуры, не только цветом
- [ ] `science` и `features` переведены на en/ru/uz

# SkyBlink: общий документ команды v4 (единый технический контракт)

> **Обновлено: 14 ноября 2026, 13:30 (Ташкент).** Это единственный источник правды для структуры репозитория, ролей, Python-интерфейсов, REST API и frontend-контрактов. При конфликте с продуктовыми/персональными планами следовать этому файлу.

## §0. Проверено живыми запросами 14.11.2026 — приоритет над всем ниже

> ⏰ **ДЕДЛАЙН: воскресенье 15 ноября, 23:59 по местному времени** (проверено на spaceappschallenge.org/2026). На момент v4 осталось ~34 часа, а не 48. Таймлайн §10 пересчитан под это.

| Вопрос | Проверенный ответ | Как проверено |
|---|---|---|
| Как искать снимки | **SIA2** `https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_dr1&POS=circle+RA+DEC+0.001&RESPONSEFORMAT=CSV` (+ то же для `spherex_qr3`). WISE 0855: DR1 = **258 снимков за ~9 с**; QR3 = 0. TAP (`spherex.plane`) даёт те же 258, но за 20–60 с — **использовать SIA2** | живой запрос |
| Поля SIA2, которые нужны | `access_url`, `t_min` (MJD), `energy_bandpassname` (`SPHEREx-D1..D6`), `em_min/em_max` (м), `obs_id`, `obs_collection`, `s_pixel_scale` = **6.150**, `cloud_access` (копия в публичном S3 `nasa-irsa-spherex`) | живой запрос |
| Пиксель | **6.15″** (SIA2 `s_pixel_scale` и официальная документация), не 6.2″ | док + запрос |
| Cutout | `access_url + "?center={ra},{dec}d&size={градусы}"`. 345″ (0.0958°) → **56×56 px**, т.е. `size` в градусах подтверждён | живая загрузка |
| ⚠️ Ловушка IRSA | Под нагрузкой ответ **HTTP 200, `application/fits`, тело `"Server busy, retry later."`** (25 байт). Проверять `body.startswith(b"SIMPLE")`, ретраить с паузой 3–12 с | живая загрузка |
| Вес и время cutout | ~**4 МБ и ~12 с** на одну вырезку 345″; почти всё — `EPSF`. В кэш класть без `EPSF` | живая загрузка |
| Слои | `IMAGE, FLAGS, VARIANCE, ZODI, EPSF, WCS-WAVE`; `VERSION='7.0.5'` в HDU 0; WCS `RA---TAN-SIP`; спектральный `WAVE-TAB` | живая загрузка |
| WCS-WAVE в Python | Официальный туториал IRSA читает так: `WCS(hdr, fobj=hdul, key="W")`, затем `.sip = None`, `pixel_to_world(x, y)` → (λ, Δλ). Если не сработает — билинейная интерполяция по 4 узлам (точность ~1 нм по документации) | туториал + док |
| Эпохи | Реальный cadence: WISE 0855 — 3 кластера (май 2025; окт–дек 2025; апр–май 2026), Barnard — 3, ε Ind B — 4, RW Aur — 3, R Dra — **непрерывно** (у полюса эклиптики). Внутри кластера снимки идут неделями → **`epoch_gap_days` по умолчанию 60**, не 3. Для R Dra — фолбэк: бины по 30 дней | TAP по 5 целям |
| Пары детекторов | D1+D4, D2+D5, D3+D6 — один `obs_id` и одно время (одна экспозиция) | TAP |
| Диапазоны детекторов, мкм | D1 0.746–1.117 · D2 1.103–1.650 · D3 1.630–2.435 · D4 2.403–3.847 · D5 3.811–4.430 · D6 4.412–5.010 | SIA2/TAP `em_min/em_max` |
| Скорость холодного blink | SIA2 ~9 с + 24 вырезки × ~12 с (6 потоков) ≈ **1–2 мин** → синхронный ответ за 25 с невозможен. **`/api/blink` асинхронный** (см. §6) | расчёт по замерам |
| 5 тестовых объектов | **Явно названы на странице челленджа** («Test your tool on Barnard's Star, Epsilon Indi B, WISE 0855…, RW Aurigae and R Draconis»). Это не наш выбор, а требование задачи | страница челленджа |
| FLAGS | Таблица битов — **Table 16 в SPHEREx Explanatory Supplement** (на странице data products её нет). До разбора: маскировать любой ненулевой флаг, но если так теряется > 50% пикселей — отключать маску и писать warning | док |

Подробности и сырые цифры — `docs/DATA_NOTES.md`.

> Этот файл прикладывается к **каждому** персональному плану. Все трое — full-stack. Работа поделена **по фичам «насквозь»**: каждый делает свою часть и в Django, и в Next.js. Здесь описано всё, что должно совпадать у всех: контракты, папки, точки синхронизации.

## 1. Проект
Веб-инструмент для NASA Space Apps 2026, челлендж «Planet X and SPHEREx». Пользователь вводит название объекта или координаты и видит анимацию (blink) снимков SPHEREx разных дат, на которой видно движение и переменность объектов. Главная ценность — **простота для обычных людей**.

**Тестовые объекты (прямо указаны в тексте челленджа — «Test your tool on…»):** Barnard's Star, Epsilon Indi B, WISE 0855−0714 (RA 08h55m10.831s, Dec −07°14′42.53″), RW Aurigae, R Draconis.

**Стек:** Django + DRF (Render/Railway) · Next.js App Router + TypeScript + Tailwind + next-intl + zustand + Recharts (Vercel) · Aladin Lite v3. Языки: en, ru, uz (латиница).

> [!IMPORTANT]
> Проект — в **`D:\skyblink\`** (один репозиторий на GitHub). Папку `D:\digital-lib` **не трогать**.

## 2. Роли (вертикальные срезы; все участники full-stack)

| # | Роль | Backend | Frontend |
|---|---|---|---|
| **1** | **Core Viewer** — «сердце» проекта | Доступ к SPHEREx, эпохи, стек, репроекция, PNG; `/api/blink`, `/api/frame` | Страница `/view`, BlinkPlayer, режимы frames/diff/sum, FOV, детектор, состояние в URL, layout со слотами |
| **2** | **Science Layers** — научные фишки | Gaia/CatWISE, спектры, кривые блеска, RGB | Наложение каталогов со стрелками, панель спектра, кривая блеска, RGB-контролы, Aladin-панель |
| **3** | **Platform & People** — платформа и пользователи | Каркас Django, деплой, `/api/health`, `/api/resolve`, `/api/presets`, находки | Каркас Next.js + i18n, главная (поиск + пресеты), `/embed`, онбординг, Простой режим, About, находки, доступность, подача |

## 3. Владение папками

```
D:\skyblink\
├─ research\core\                    → #1
├─ research\science\                 → #2
├─ backend\
│  ├─ skyblink\ (settings, urls.py)  → #3 (каждый добавляет в urls.py только строку include своего app)
│  ├─ core\                          → #1  общая библиотека: SPHEREx, кэш, сетка/WCS, рендер PNG
│  ├─ viewer\                        → #1  эндпоинты blink/frame
│  ├─ science\                       → #2  эндпоинты catalog/spectrum/lightcurve/rgb
│  ├─ platform_api\                  → #3  health/resolve/presets
│  ├─ findings\                      → #3
│  ├─ scripts\prefetch.py            → #1 (#2 добавляет функцию прогрева своих эндпоинтов)
│  └─ requirements.txt, render.yaml  → #3 (остальные добавляют строки через PR)
├─ frontend\
│  ├─ app\[locale]\layout.tsx, page.tsx, about\, findings\, embed\ → #3
│  ├─ app\[locale]\view\page.tsx     → #1
│  ├─ features\viewer\               → #1
│  ├─ features\science\              → #2
│  ├─ features\home\, findings\, onboarding\, settings\ → #3
│  ├─ lib\store.ts                   → #1 создаёт; #2 и #3 добавляют свои поля через PR
│  ├─ lib\api\viewer.ts | science.ts | platform.ts → #1 | #2 | #3
│  ├─ lib\mocks\                     → каждый свои файлы
│  └─ messages\{en,ru,uz}\<namespace>.json → у каждого свои namespace (см. §7)
├─ shared\presets.json               → #3 (тексты); координаты, fov и mode подбирает #1
├─ shared\api-samples\*.json         → каждый для своих эндпоинтов
└─ docs\                             → DATA_NOTES (#1 + #2), PITCH и README (#3)
```

## 4. Внутренний Python-интерфейс `backend/core` (владелец #1; им пользуется #2)

Сигнатуры фиксируются на **Sync 1 (H4)**. До этого #2 работает на изолированном spike-коде, затем переносит нужные части в общий `core`. Не закреплять поля/расширения FITS, пока они не проверены на реальном файле DR1/QR3.

```python
# core/spherex.py
@dataclass
class ImageMeta:
    obs_id: str
    date_mjd: float
    date_iso: str
    detector: int                 # 1..6
    release: str                  # dr1 | qr3
    collection: str               # фактическая SIA2 collection
    access_url: str               # из access_url SIA2
    raw_metadata: dict            # исходные поля SIA2 для диагностики

def find_images(
    ra: float, dec: float, radius_arcsec: float,
    releases: tuple[str, ...] = ("dr1", "qr3"),
    include_deep: bool = False,
) -> list[ImageMeta]: ...

def fetch_cutout(
    meta: ImageMeta, ra: float, dec: float, size_arcsec: float
) -> "astropy.io.fits.HDUList": ...  # с файловым кэшем; единицы cutout URL проверены тестом IRSA

# core/grid.py
def make_grid(ra: float, dec: float, fov_arcsec: float, pixscale_arcsec: float = 6.15) -> tuple["WCS", tuple[int, int]]: ...
def sky_to_pix(wcs, ra, dec) -> tuple[float, float]: ...
def pix_to_sky(wcs, x, y) -> tuple[float, float]: ...

# core/epochs.py
def group_epochs(metas: list[ImageMeta], gap_days: float = 60, fallback_bin_days: float = 30) -> list[list[ImageMeta]]: ...
    # 60 дней — по реальному cadence 5 целей (§0); конфигурируемо. < 2 эпох → бины по 30 дней (R Dra)
def limit_per_epoch(epoch: list[ImageMeta], max_n: int = 8) -> list[ImageMeta]: ...  # равномерно по времени

# core/imaging.py
def masked_image(hdul, flag_policy: dict) -> "np.ma.MaskedArray": ...  # биты FLAGS только из официальной таблицы
def pixel_wavelength(hdul, x, y) -> tuple[float, float]: ...  # central wavelength, bandwidth; WCS-WAVE для визуализации
def reproject_to(hdul, wcs, shape) -> "np.ndarray": ...
def render_png(arrays: list, stretch="zscale_asinh", symmetric=False) -> list[bytes]: ...  # одна шкала в пределах одного detector/sequence
```

## 5. Frontend-контракт: общий стор и слоты (владелец #1)

```ts
// lib/store.ts (zustand)
type ViewerState = {
  target: { ra: number; dec: number; name?: string } | null;
  fov: number; mode: 'frames' | 'diff' | 'sum'; detector: 'all' | 1|2|3|4|5|6;
  frameIndex: number; zoom: number; pan: { x: number; y: number };
  blink: BlinkResponse | null;            // ответ /api/blink
  selected: { x: number; y: number; ra: number; dec: number } | null;  // клик по пикселю (#2 строит спектр)
  overlays: { gaia: boolean; catwise: boolean; badPixels: boolean; pmYears: number };  // #2
  simpleMode: boolean;                     // #3
};
```
`features/viewer/ViewerLayout.tsx` (#1) принимает слоты:
- `overlay` — SVG поверх canvas; получает `{zoom, pan, sizePx}` (сюда #2 вставляет CatalogOverlay);
- `toolbarExtra` — дополнительные кнопки (#2: каталоги и RGB; #3: «Я нашёл!»);
- `sidePanel` — Aladin (#2);
- `bottomTabs: {key, labelKey, node}[]` — «Что я вижу?» (#3), «Спектр», «Кривая блеска», «Цвета» (#2).

В Простом режиме (`simpleMode=true`) каждый сам скрывает свои продвинутые контролы.

## 6. REST API (контракт; менять только по согласию всех)
Базовый URL: `NEXT_PUBLIC_API_URL`.

| Метод | Эндпоинт | Параметры | Ответ | Владелец |
|---|---|---|---|---|
| GET | `/api/health` | — | `{"status":"ok"}` | #3 |
| GET | `/api/presets` | — | `shared/presets.json` | #3 |
| GET | `/api/resolve` | `q` | `{ra, dec, name, source}` | #3 |
| GET | `/api/blink` | `ra, dec, fov=300, detector=all\|1..6, mode=frames\|diff\|sum` | `200` + ответ ниже (если в кэше) **или** `202 {job_id, status}` | #1 |
| GET | `/api/blink/status/<job_id>` | — | `{status: queued\|running\|done\|error, progress: 0..1, stage, result?, error_code?}` | #1 |
| GET | `/api/frame/<id>.png` | — | PNG | #1 |
| GET | `/api/catalog` | `ra, dec, fov, source=gaia\|catwise` | `{sources:[{id, x, y, mag, pmra, pmdec, dx_per_yr, dy_per_yr, match_status}]}` | #2 |
| GET | `/api/badpixels` | `ra, dec, fov, detector` | PNG-маска (прозрачная) | #2 |
| GET | `/api/spectrum` | `ra, dec, source=allsky_cube\|spectral_images` | `{points:[{wavelength_um, flux, err, date_iso?}], features:[{key, wavelength_um}], quality}` | #2 |
| GET | `/api/lightcurve` | `ra, dec, detector` | `{points:[{date_iso, flux, err}] , quality}` | #2 |
| GET | `/api/rgb` | `ra, dec, fov, r, g, b` (мкм) | PNG | #2 |
| GET/POST | `/api/findings` | POST `{ra, dec, note, nickname?, website?}` | `{id,…}` / список | #3 |

```json
// Illustrative response shape only; timestamps, counts and wavelengths below are not measurements for this target.
// GET /api/blink?ra=133.79513&dec=-7.24515&fov=300&detector=all&mode=frames
{
  "target": {
    "ra": 133.79513,
    "dec": -7.24515,
    "name": "WISE 0855-0714",
    "coordinate_epoch": null
  },
  "fov_arcsec": 300,
  "grid": {
    "id": "grid-001",
    "width": 49,
    "height": 49,
    "pixel_scale_arcsec": 6.15,
    "wcs_header": {
      "CTYPE1": "RA---TAN",
      "CTYPE2": "DEC--TAN",
      "CRVAL1": 133.79513,
      "CRVAL2": -7.24515,
      "CRPIX1": 25.0,
      "CRPIX2": 25.0
    }
  },
  "frames": [
    {
      "id": "cache-key",
      "url": "/api/frame/cache-key.png",
      "date_iso": "2025-06-02",
      "date_mjd": 60828.4,
      "n_images": 14,
      "detector": 1,
      "wavelength_range_um": [0.75, 1.09],
      "target_wavelength_um": 0.92,
      "target_bandwidth_um": 0.022,
      "kind": "epoch"
    }
  ],
  "warnings": [{"code": "few_epochs", "severity": "info"}],
  "flags_summary": {"bad_pixel_fraction": 0.03}
}
```

**Семантика ответа:**
- `frames` отсортированы сначала по `detector`, затем по времени. Фронтенд фильтрует кадры по активному детектору и проигрывает только одну временную последовательность. Нельзя проигрывать вперемешку кадры разных детекторов.
- `detector=all` не означает смешивание фотометрических полос: он возвращает независимые наборы кадров с полем `detector`.
- `mode=frames`: один кадр на эпоху и детектор с metadata о длине волны в целевом пикселе; `mode=diff`: разностный кадр только относительно wavelength-matched эпох того же детектора; `mode=sum`: один итоговый кадр на detector и wavelength bin.
- `wavelength_range_um` — справочная полоса детектора. `target_wavelength_um` и `target_bandwidth_um` описывают LVF в положении цели в данном наблюдении. Для разных эпох эти значения могут различаться.
- `grid.wcs_header` должен содержать полный сериализованный WCS header (включая CD/PC/SIP при наличии). Приведённый выше объект — сокращённый пример, не готовая полная WCS-карта.
- FITS WCS `CRPIX` использует 1-based convention; canvas/PNG пиксели — 0-based. Преобразование проверяется тестом центра и четырёх углов.

Пиксельные координаты `/api/catalog` должны относиться к той же `grid` и тому же `fov`. Если каталог рассчитывается независимо, API должен возвращать `grid_id`/версию сетки или принимать полное описание сетки, чтобы исключить расхождение проекций.

Ошибки — машинными кодами (`no_data`, `few_epochs`, `irsa_timeout`, `fov_too_large`, `not_found`, `invalid_coordinates`, `unsupported_product`, `wavelength_mismatch`); тексты переводятся на фронтенде через `errors.<code>`. Для `/api/health` использовать только `{"status":"ok"}`. Для URL страницы использовать `det`; при вызове API преобразовывать его в `detector`.

**Асинхронность (обязательно с первого дня):** холодный запрос занимает 1–2 минуты (§0) и не влезает в таймаут gunicorn/Render. При промахе кэша `/api/blink` ставит задачу в фоновый `ThreadPoolExecutor` (Celery не нужен) и сразу отвечает `202`. Фронт опрашивает `/status` раз в 1.5 с и показывает `stage` через i18n («Ищем снимки в архиве NASA…», «Скачиваем 24 снимка…», «Собираем кадры…»). Пресеты всегда отдаются из кэша со `200`.

## 7. i18n
- Файлы: `messages/{en,ru,uz}/{namespace}.json`, объединяются в `i18n/request.ts` (настраивает #3).
- Namespaces: #1 → `viewer`; #2 → `science`, `features`; #3 → `common`, `home`, `onboarding`, `about`, `findings`, `errors`, `presets`.
- **Каждый сам пишет en/ru/uz для своих namespace** (агент переводит). #3 вычитывает ru/uz в конце. Скрипт `scripts/check_i18n.mjs` (#3) в CI находит пропущенные ключи.

## 8. `shared/presets.json`
```json
[{
  "slug": "wise-0855", "ra": 133.79513, "dec": -7.24515,
  "type": "brown_dwarf",
  "fov": 300, "default_mode": "diff", "default_detector": 6,
  "title": {"en": "", "ru": "", "uz": ""},
  "short": {"en": "", "ru": "", "uz": ""},
  "what_you_see": {"en": "", "ru": "", "uz": ""}
}]
```

## 9. Git
- Ветки `p1/*`, `p2/*`, `p3/*`; в `main` только через PR. Ревью делает любой другой участник, мержит автор. CI должен быть зелёным.
- Маленькие частые коммиты; перед работой `git pull --rebase`. Секреты только в `.env`.

## 10. Таймлайн и созвоны (по 10 минут) — под реальный дедлайн

Окно подачи закрывается **вс 15.11 в 23:59 по местному времени**. Время ниже — Ташкент, старт сб 14:00. Ночь на сон заложена: уставшая команда в 3 часа ночи ломает больше, чем чинит.

| Когда | Синхронизация | Что должно быть |
|---|---|---|
| сб 14:00 | Старт | #3 — репозиторий, каркасы, деплой hello-world; #1 — `spike.py` на реальных данных; #2 — spike Gaia/CatWISE |
| **сб 17:00** | **Sync 1** | Контракты §4–§6 зафиксированы; #1 показал реальный GIF/diff; hello-world на проде |
| сб 22:00 | Sync 2 | `/api/blink` (async) + плеер для 1 объекта; главная и поиск работают |
| сб 01:00 – 08:00 | сон | — |
| **вс 12:00** | **Sync 3: MVP** | 5 пресетов end-to-end на проде, en/ru/uz |
| вс 16:00 | Sync 4 | diff, Gaia/CatWISE-стрелки, спектр-preview, онбординг |
| **вс 18:00** | **Feature freeze** | Дальше только баги и полировка |
| вс 20:00 | Sync 5 | Кэш пресетов прогрет, видео снято, проверено на телефоне |
| **вс 21:30** | **Подача** | Материалы загружены (запас 2.5 часа до 23:59) |

Если к **вс 12:00** MVP не готов — режем всё из §12 «выкидываем», кроме blink, 5 пресетов, поиска, URL, diff.

## 11. Данные: что ещё осталось проверить (остальное — §0 и `docs/DATA_NOTES.md`)
- ⚠️ Биты `FLAGS` по Table 16 Explanatory Supplement → выбранная маска в `DATA_NOTES.md` (#2).
- ⚠️ Допуск совпадения длины волны (`wl_tol_um`) по реальным `target_wavelength_um` в DR1 (#1). Стартовое значение для preview: 0.05 мкм.
- ⚠️ Есть ли WISE 0855 и ε Ind B в CatWISE2020 (в Gaia DR3, скорее всего, нет) (#2).
- Сдвиг за всю базу при 6.15″/px: Barnard ≈ 1.9 px, WISE 0855 ≈ 1.3 px, ε Ind B ≈ 1.1 px (по примерным PM; уточнить по каталогам). Голого blink мало → diff, зум, PM-стрелки, сравнение с WISE (база ~15 лет).

## 12. Что выкидываем при нехватке времени (по порядку)
ML (отложен решением команды) → аккаунты → RGB → bad-pixel маска → мини-обучение → кривая блеска.
**Нельзя выкидывать:** blink, 5 пресетов, поиск, URL-параметры, diff, Gaia-стрелки, спектр (бонус от жюри), i18n, мобильную версию, онбординг, базовую доступность.


## 13. Научные и data-processing правила (обязательны)

### SPHEREx releases и коллекции
- Для новых поисков использовать SIA2 endpoint `https://irsa.ipac.caltech.edu/SIA?` (проверено: в ~3–6 раз быстрее TAP, сразу отдаёт `access_url`).
- Wide survey collections: `spherex_dr1` и `spherex_qr3`; Deep: `spherex_dr1_deep` и `spherex_qr3_deep`; DR1 All-Sky Cube: `spherex_dr1_cube`.
- Для полного текущего набора spectral images искать DR1 и QR3. QR2 не искать через SIA2; не смешивать QR2 с DR1/QR3 без отдельного калибровочного обоснования.
- SIA2 результат содержит `access_url`; не конструировать URL вручную. Cutout service вызывается через URL найденного MEF с параметрами `center` и `size`; единицы/формат параметров закрепить тестом из официального tutorial.

### Spectral Image MEF
- DR1/QR3: `IMAGE`, `FLAGS`, `VARIANCE`, `ZODI`, `EPSF`, `WCS-WAVE`. QR2: `PSF` вместо `EPSF`.
- `IMAGE` в MJy/sr; `VARIANCE` в (MJy/sr)^2. `ZODI` — модель зодиакального фона, не вычтенная из `IMAGE`.
- `WCS-WAVE` — lookup table с X, Y и VALUES (центральная длина волны и bandwidth). Для визуализации можно интерполировать по четырём ближайшим контрольным точкам. Для научного анализа использовать `CWAVE`/`CBAND` из Spectral WCS calibration product.
- Читать как в официальном туториале: `WCS(hdr, fobj=hdul, key="W")`, `.sip=None`, `pixel_to_world`. Документация предупреждает, что не все читатели FITS это поддерживают, поэтому обернуть в try и иметь фолбэк — билинейную интерполяцию по 4 узлам таблицы.
- `IMAGE` не содержит вычтенного ZODI. Для **отображения** вычитание `ZODI` и медианы кадра допустимо (документировать в коде); для **фотометрии** — работать с `IMAGE` и локальным фоном, единицы MJy/sr не менять.
- Значения FLAGS декодировать только по официальной таблице битов соответствующего release; хранить flag policy/version в `DATA_NOTES.md`.

### All-Sky Cube
- DR1 All-Sky Cube — отдельный продукт, 12,288 HEALPix tiles, около 1.8° × 1.8° каждый, 512 × 512 × 102; 102 канала и pixel scale около 12.9″.
- Куб имеет собственную структуру HDU (`IMAGE`, `NHITS`, `FLAGS`, `SPECTRAL_CHANNELS`, `WCS-WAVE`) и отличается от Spectral Image MEF.
- Использовать его для не-временного спектрального контекста. Не выдавать его каналы за временные эпохи и не использовать для temporal blink.
- Каналы 51 и 52 помечены как пустые (`BLANKCH`); корректно учитывать их при построении спектра.

### Временные ряды, detector и WCS
- `make_grid(..., pixscale_arcsec=6.15)` относится к Level 2 Spectral Images. Для All-Sky Cube использовать его собственную WCS и реальный pixel scale (~12.9″); не переиспользовать Level 2 grid автоматически.
- Один detector соответствует своей полосе/диапазону. Stack, median reference и diff строить **внутри одного detector**; не усреднять шесть детекторов в одну серую картинку. Но одного совпадения detector недостаточно: LVF wavelength зависит от координаты пикселя, поэтому сравнивать/стекать кадры для target только при согласованных `target_wavelength_um` (допуск фиксируется после spike) либо разбивать на wavelength bins.
- Эпохи кластеризовать по `t_min` (MJD). Реальный cadence изучен (§0): **`epoch_gap_days=60`** (configurable); при < 2 эпохах — бины по 30 дней. Значение 3 дробит один 6-месячный проход на куски с разной длиной волны.
- При репроекции использовать WCS конкретного изображения и общую grid для target + detector sequence. Не подменять полный WCS четырьмя числами.
- Масштаб отображения фиксировать по всем wavelength-matched эпохам одного detector, не по разным detector. Если wavelength не совпадает, не интерпретировать изменение яркости как переменность.
- При движущейся цели переносить координаты на эпоху снимка с учётом proper motion, если известен PM и эпоха каталога. Для неизвестной эпохи координат показывать предупреждение.

### Gaia/CatWISE и интерпретация
- Gaia DR3 PM/reference epoch учитываются при прогнозе положения на дату SPHEREx; CatWISE также имеет свою эпоху/астрометрические параметры.
- Отсутствие совпадения в Gaia не доказывает новый объект. UI пишет «кандидат без уверенного совпадения в выбранном каталоге», а не «открытие».
- Хранить match radius, epoch propagation, quality filters и catalog release в метаданных результата.

### Фотометрия
- Не строить одну light curve из сырых flux разных detector bands. Выбирать один detector/полосу и одинаковый метод измерения для всех эпох.
- Для научной фотометрии учитывать PSF/ePSF, маски FLAGS, фон и апертурную коррекцию. Если это не реализовано/не проверено, помечать график как exploratory/preview.
- Спектр из одиночного пикселя нельзя называть полноценным спектром источника без корректной выборки по LVF-экспозициям, PSF и калибровок.

## 14. Проверенные официальные источники (14.11.2026)
- Releases: https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-releases/
- Data products: https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/
- Data access / SIA2: https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/
- Instrument: https://spherex.caltech.edu/page/instrument
- IRSA tutorials: https://caltech-ipac.github.io/irsa-tutorials/spherex/


## 15. Сроки Space Apps 2026
Официальная страница Space Apps 2026 указывает окно отправки проекта: открывается 14 ноября в 09:00 и закрывается 15 ноября в 23:59 по локальному времени. Поэтому внутренний таймлайн H0–H48 — ориентир, а не гарантия полного 48-часового окна. Команда должна поставить внутренний feature freeze и отправку с запасом до фактического локального дедлайна.
Источник: https://www.spaceappschallenge.org/2026/


## 16. API reliability and security
- Validate `ra` in [0, 360), `dec` in [-90, 90], `fov` within the documented limit, detector in `all|1..6`, and mode in the enum. Reject NaN/Infinity and malformed coordinate strings.
- Never accept an arbitrary FITS URL from the browser. Backend downloads only trusted `access_url` values returned by IRSA SIA2; this avoids turning the API into an open URL proxy.
- `/api/frame/<id>.png` uses an opaque cache key, not a filesystem path supplied by the client. Resolve it only inside the configured cache root.
- Apply request timeouts, bounded retries with backoff, concurrency limits for IRSA downloads, and rate limits on expensive endpoints.
- Return stable machine-readable error codes plus appropriate HTTP status codes. Do not return raw upstream stack traces or internal file paths.
- CORS allowlist: production Vercel origin(s) plus explicit localhost development origins; no wildcard with credentials.
- Keep `.env`, API keys, and private deployment values out of Git. Do not store large generated FITS files in the repository.
- Exception for the demo: the 5 preset blink responses (JSON + small PNG frames, ~49×49 px each, a few hundred KB total) MAY be committed to `backend/viewer/static_cache/`, because the free Render disk is wiped on restart. FITS never go to Git.
- IRSA downloads: max 6 concurrent, bounded retries with backoff, and treat any body not starting with `b"SIMPLE"` as a retryable "Server busy" response.

# План участника #1: Core Viewer (full-stack)

> **Редакция 3 — 14 ноября 2026.** Все интерфейсы и JSON-схемы сверять с `00_COMMON.md` (единственный источник правды; сначала прочитать его §0 — проверенные факты). Готовый стартовый скрипт: `research/core/spike.py` (SIA2 DR1+QR3 → эпохи → вырезки → стек → GIF + diff; офлайн-самотест `--selftest`).

> **Агенту:** сначала прочитай `00_COMMON.md`. Ты делаешь «сердце» проекта насквозь: библиотеку данных `backend/core`, API `backend/viewer`, страницу `/view` и плеер в `frontend/features/viewer`. Ты же создаёшь общий стор `lib/store.ts` и `ViewerLayout` со слотами, в которые встраиваются #2 и #3, поэтому **их надо выложить рано (к H8)**. В чужие папки не пиши. Человек не астроном, поэтому объясняй астрономию в комментариях.

## Backend: что твоё
`backend/core/` (spherex, grid, imaging, кэш) · `backend/viewer/` (`/api/blink`, `/api/frame`) · `backend/scripts/prefetch.py` · `research/core/` · половина `docs/DATA_NOTES.md`.
Зависимости: `astropy astroquery pyvo reproject photutils numpy scipy pillow requests`.

## Frontend: что твоё
`app/[locale]/view/page.tsx` · `features/viewer/*` · `lib/store.ts` · `lib/api/viewer.ts` · `messages/*/viewer.json`.

---

## H0–H4. Разведка данных (BE)
1. Запустить `python research/core/spike.py --selftest` (офлайн, ~1 с), затем `python research/core/spike.py --target wise0855 --detector 6` (SIA2 `spherex_dr1` + `spherex_qr3` → `access_url` → cutout → FITS). Deep collections проверять отдельно.
2. Для WISE 0855 и Barnard's Star: количество снимков, даты, детекторы, release/collection, HDU и WCS; не смешивать DR1/QR3 с QR2. Если у объекта нет пригодных эпох, зафиксировать это и не подменять результат синтетикой.
3. Эпохи кластеризовать по `t_min` (MJD) внутри одного detector. **`epoch_gap_days=60`** — проверено по реальному cadence 5 целей (COMMON §0); 3 дня дробит один проход на куски. Фолбэк для R Dra — бины по 30 дней. Дополнительно проверить wavelength в target pixel по WCS-WAVE и сравнивать только совместимые эпохи. Затем stack → общая сетка → **GIF**.
4. Записать в `DATA_NOTES.md` реальные SIA2 collections, access_url metadata, параметры cutout, HDU, таблицу FLAGS и особенности WCS-WAVE.
5. **Sync 1:** показать GIF, зафиксировать сигнатуры `core` (COMMON §4) и формат `/api/blink`.

Если движение плохо видно: меньше FOV, diff, более длинная временная база, корректная привязка WCS и PM-векторы Gaia. **Не складывать разные detector bands друг с другом:** это разные диапазоны длин волн.

## H4–H8. `core` + каркас фронтенда для всех (BE + FE)
- BE: `core/spherex.py` (find_images, fetch_cutout с файловым кэшем в `CACHE_DIR`, таймауты, ретраи), `core/grid.py`, `core/imaging.py` — по сигнатурам из COMMON §4. **Как можно раньше вмержить в main**, на этом стоит работа #2.
- FE: `lib/store.ts` (COMMON §5) и `features/viewer/ViewerLayout.tsx` со слотами `overlay`, `toolbarExtra`, `sidePanel`, `bottomTabs`. Можно с заглушками. **Вмержить к H8.**

## H8–H14. `/api/blink` + BlinkPlayer (BE + FE)
- BE `viewer/`: поток «SIA2 DR1/QR3 find → cutout → epoch grouping отдельно по detector → FLAGS mask по официальной таблице → inverse-variance weighted stack (с проверкой variance>0) → reproject на общий WCS grid → одна ZScale+Asinh шкала для wavelength-matched эпох этого detector → PNG». Ответ строго по COMMON §6, PNG отдаются с `Cache-Control: public, max-age=86400`. Ограничения: FOV ≤ 1800″. **Холодный запрос — асинхронно** (`202 {job_id}` + `/api/blink/status/<job_id>`, COMMON §6): он занимает 1–2 мин, 25 с не хватит. Общий таймаут задачи 180 с, ≤ 6 параллельных загрузок, ретрай на «Server busy». Коды `irsa_timeout`, `fov_too_large`, `no_data`, `few_epochs`, `unsupported_product`, `wavelength_mismatch`. `detector=all` возвращает независимые группы кадров, а не общий stack. Реальный пример ответа — в `shared/api-samples/blink_wise0855.json`.
- FE `features/viewer/BlinkPlayer.tsx` (canvas): предзагрузка PNG, `imageSmoothingEnabled=false`, play/pause, предыдущий/следующий кадр, скорость 0.5–5 кадров/с, ползунок кадров, зум 1–8× и перетаскивание, подпись даты, перекрестие. Клавиатура `Space`, `←/→`, `+/-`; свайп на мобильных; `prefers-reduced-motion` → без автоплея; aria-label из i18n.
- Клик по пикселю → `store.selected = {x, y, ra, dec}`. Использовать полный `grid.wcs_header`; помнить: canvas x/y — 0-based, FITS CRPIX — 1-based. Добавить unit-тест центра и углов.

## H14–H20. Страница `/view` + URL → MVP (FE + BE)
- `view/page.tsx`: читает `ra, dec, name, fov, mode, det, t` из URL и синхронизирует их со стором (`router.replace` без перезагрузки).
- Тулбар: frames/diff/sum (diff и sum пока могут быть отключены), FOV 2′/5′/15′/30′ с подсказкой про скорость, детектор all/1–6. В Простом режиме видны только Play и ползунок.
- Состояния: skeleton с текстом «Загружаем снимки из архива NASA…», ошибки по `errors.<code>`, пустое состояние.
- Кнопка «Поделиться» (copy link / `navigator.share`).
- BE: подобрать для 5 пресетов `fov`, `default_mode` и `default_detector` и записать в `shared/presets.json`. Стартовые значения: коричневые карлики (WISE 0855, ε Ind B) → D6 (4.4–5.0 мкм, там они ярче всего); Barnard → D2; RW Aur, R Dra → D2. `scripts/prefetch.py` прогревает кэш пресетов и кладёт JSON + маленькие PNG в `backend/viewer/static_cache/` (это можно коммитить, COMMON §16; FITS — никогда).
- **Sync 3:** 5 пресетов работают на проде.

## H20–H30. Режимы и детекторы (BE + FE)
- `mode=diff`: кадр минус медиана эпох **того же detector**, симметричная шкала (серый = 0). В UI легенда «чёрное + белое пятно рядом = движение».
- `mode=sum`: глубокое изображение отдельно для каждого detector; в ответе один кадр на detector.
- `detector=1..6`: в ответ добавить справочный `wavelength_range_um`; в UI подписать полосу. `detector=all` — отдельные последовательности; не интерливить и не суммировать полосы.
- Режим «сравнение двух эпох»: две эпохи рядом или шторка (slider-compare).
- Оптимизация: параллельное скачивание cutout (ThreadPool), кэш готовых ответов blink.

## H30–H36. Холодные запросы и стабильность
- Проверить 5–10 случайных координат (не пресетов): время, ошибки, понятные сообщения.
- Тесты: `core/tests` (grid, кластеризация эпох, render_png на синтетике), `viewer/tests` (blink на закэшированных фикстурах без сети).
- FE: мобильная проверка плеера на 375 px.

## H36–H46. Полировка и демо
- Баги из баг-листа (метка `p1`).
- Бонус, если всё готово: management-команда `refresh_releases` (обновляет список DR1/QR3 и сбрасывает только устаревший кэш); простой автодетектор пар «+/−» на diff (`DAOStarFinder`), подсветка кандидатов.
- Дать #3 2–3 лучших GIF и абзац «как мы обрабатываем данные» для README и питча.
- Финальный прогрев кэша на проде.

## Чек-лист
- [ ] `core` вмержен в main к H8, им пользуется #2
- [ ] Стор и ViewerLayout вмержены к H8, слоты работают
- [ ] 5 пресетов из кэша открываются быстрее чем за 1 секунду; движение Barnard's Star и WISE 0855 видно
- [ ] URL полностью восстанавливает вид
- [ ] frames/diff/sum/FOV/детекторы работают на десктопе и мобильных
- [ ] `viewer` namespace переведён на en/ru/uz


---

## Обязательные технические уточнения

1. **Текущие коллекции:** для новых данных искать `spherex_dr1` и `spherex_qr3`; при необходимости — `spherex_dr1_deep` и `spherex_qr3_deep`. SIA2 endpoint: `https://irsa.ipac.caltech.edu/SIA?`. Брать `access_url` из результата SIA2, не собирать путь к FITS вручную.
2. **Временной blink:** использовать Level 2 Spectral Image MEF. DR1 All-Sky Cube (`spherex_dr1_cube`) — не временная последовательность; не превращать его 102 спектральных каналов в кадры по датам.
3. **MEF DR1/QR3:** `IMAGE`, `FLAGS`, `VARIANCE`, `ZODI`, `EPSF`, `WCS-WAVE`. В QR2 вместо `EPSF` — `PSF`; QR2 не смешивать с DR1/QR3 в одном stack без явной калибровочной проверки.
4. `IMAGE` — MJy/sr; `VARIANCE` — (MJy/sr)^2; `ZODI` не вычтен из `IMAGE`. Не применять произвольную нормировку/вычитание, скрывающую реальную переменность.
5. `WCS-WAVE` содержит lookup table X/Y/VALUES. Для preview можно использовать билинейную интерполяцию; для научного анализа нужны `CWAVE`/`CBAND` из Spectral WCS calibration product. Это отдельная задача, не блокирующая MVP blink.
6. Не предполагать, что каждый SIA результат содержит все шесть detector images: archive указывает, что часть наблюдений может не включать все шесть bands.
7. Не считать «нет Gaia match» доказательством нового объекта. UI и pitch используют формулировку «кандидат, требующий проверки».
8. Кэш: использовать абстракцию `CACHE_DIR` и конфигурируемый backend. Render local filesystem не считать persistent без включённого и проверенного persistent disk/object storage. Не коммитить большие FITS/PNG наборы в Git; для демо хранить небольшие проверенные fixtures или object storage.
9. Не считать один FOV/epoch threshold универсальным. Хранить `epoch_gap_days` как конфиг и документировать фактический cadence по каждому тестовому target.
10. Для координат цели с высоким proper motion использовать координатную эпоху/PM при сравнении с наблюдениями; не сравнивать все изображения с фиксированной координатой J2000 без поправки.

**Источники:**  
- https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-releases/  
- https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/  
- https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/  
- https://spherex.caltech.edu/page/instrument


### Критически важно: LVF и честное сравнение эпох
У SPHEREx длина волны меняется по координате пикселя внутри каждого детектора. Поэтому два кадра одного detector могут показывать одну и ту же небесную точку на разных длинах волн. Перед stack/diff:
- вычислить `target_wavelength_um` и `target_bandwidth_um` для положения цели в каждом исходном наблюдении;
- выбрать wavelength-match tolerance на основании реальных bandwidth/калибровки и записать его в `DATA_NOTES.md`;
- сравнивать/складывать только совместимые наблюдения либо группировать их в отдельные wavelength bins;
- если подходящих эпох мало, отключить scientific diff/variability claim и показать предупреждение;
- сохранять wavelength metadata в API для каждого кадра.

Одинаковый detector и одинаковая общая шкала яркости сами по себе **не гарантируют**, что временное сравнение фотометрически корректно.

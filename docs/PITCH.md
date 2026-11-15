# PITCH & SUBMISSION — SkyBlink (владелец: #3, но вычитывают все)

> Источник требований: официальные Project Submission Guide и Judging & Awards Guide Space Apps 2026 (проверено 14.11.2026).
> **Всё, что идёт в форму и по ссылкам, — только на английском.** Русские пометки ниже — для команды, в форму их не копировать.

---

## 0. Чек-лист допуска к глобальному судейству (нарушение любого пункта = вылет)

- [ ] **Дедлайн = 23:59 вс 15.11 по времени нашего Local Event.** Спросить Local Lead точное время сегодня. Внутренняя подача — **вс 21:30**.
- [ ] Все участники зарегистрированы, на **одном** Local Event, **не в waitlist**, видны во вкладке **Members**. После закрытия подачи добавить никого нельзя.
- [ ] Все обязательные поля формы заполнены, **на английском**.
- [ ] Демо: **видео ≤ 30 секунд** (31 секунда = дисквалификация) **или** ≤ 7 слайдов. Видео на YouTube/Drive, ссылка **публичная**, без входа и запросов доступа. Речь можно на узбекском/русском, но **английские субтитры обязательны**.
- [ ] Ссылка на финальный проект (сайт на Vercel) и **публичный** GitHub — открываются в режиме инкогнито.
- [ ] Поле References: перечислены **все** чужие код, данные, изображения (даже open source).
- [ ] Поле SI (ИИ): честно описано, где и как использовали ИИ (§5).
- [ ] Картинки/видео, сгенерированные ИИ, имеют **видимый водяной знак**. Никаких логотипов NASA, флагов, эмблем миссий в сгенерированном контенте. Безопаснее: в видео только скринкаст нашего сайта, без ИИ-картинок.
- [ ] Код, написанный с ИИ: отметка в README и в шапке файлов (см. §5).
- [ ] Обе галочки согласия на странице подачи отмечены, нажата **«Submit for Judging»**.
- [ ] Если в команде кто-то младше 18: не использовать их фото, видео и голос в демо (FAQ Space Apps).

---

## 1. Критерии (официальные, каждый 1–5) → что показываем

| Критерий | Что даёт 5 баллов (по гайду) | Наш аргумент |
|---|---|---|
| **Impact** | значимая проблема, широкий охват, вдохновляет | Большинство коричневых карликов найдено волонтёрами (Backyard Worlds). SkyBlink даёт тот же метод «blink» для данных SPHEREx любому человеку, на en/uz/ru |
| **Creativity** | новый подход, а не повтор | Сравнение эпох с учётом длины волны (LVF) — честно, а не «как у всех»; SPHEREx рядом с WISE (база 15 лет); спектр по клику; «Что я вижу?» простым языком |
| **Validity** | научно корректно, работает, **удобно** | Все 5 тестовых объектов челленджа работают; предупреждения вместо фальшивых «открытий»; Простой режим, онбординг, мобильная версия, доступность |
| **Relevance** | закрывает задачу, NASA-данные — ядро | Данные SPHEREx (IRSA) — основа каждого кадра. Таблица соответствия задаче — §4 |
| **Presentation** | ясная история, качественное демо | 30-секундное видео по официальному таймингу (§2) + аккуратная страница проекта |

---

## 2. Демо-видео (30 секунд, по официальному таймингу гайда)

Формат: скринкаст сайта + голос (любой язык) + **английские субтитры**. Музыка — только с лицензией (или без музыки). Снимает и монтирует один человек; начинать вс 16:00, готово к 20:00.

| Время | Кадр | Текст (EN-субтитры) |
|---|---|---|
| 0:00–0:02 | Лого SkyBlink + имена | "We're team ___, and this is SkyBlink." |
| 0:02–0:05 | Анимация «два снимка → точка сдвинулась» | "Pluto was found by blinking two photos of the sky. NASA's SPHEREx now has images of over a billion objects." |
| 0:05–0:10 | Главная, поле поиска | "SkyBlink: spot moving and changing stars in SPHEREx data — no astronomy degree needed." |
| 0:10–0:20 | Ввод «WISE 0855» → Play → режим Diff (пара белое+чёрное) → стрелка CatWISE → бейдж «not in Gaia — candidate to verify» → клик → спектр | "Type any star or coordinates. SkyBlink stacks real SPHEREx images, compares them at the same wavelength, and shows what moved." |
| 0:20–0:30 | Переключение en → uz → ru; телефон; QR-код ссылки | "In three languages, on any phone — so anyone can help find the next brown dwarf. Try it: [link]" |

Проверка перед загрузкой: длительность ≤ 0:30 (смотреть по файлу, а не на глаз), субтитры читаются на телефоне, ссылка открывается в инкогнито.

### 2a. Вариант сценария «вау-моменты» (15.11, факты сверены с тем, что приложение реально показывает)

| Время | Кадр | Текст (EN-субтитры) |
|---|---|---|
| 0:00–0:06 | Тёмное небо, ничего не видно | "NASA's SPHEREx maps the whole sky in infrared, over and over. Cold brown dwarfs hide in it — too faint and cold for ordinary telescopes." |
| 0:06–0:13 | Пресет WISE 0855 → «Сравнить все длины волн» → ползунок 0.75 → 5.0 мкм: в начале пусто, в D6 объект появляется | "Slide from 0.75 to 5 micrometres: stars fade, and the coldest known brown dwarf appears only at the long end." |
| 0:13–0:21 | Режим «Разница»: чёрно-белая пара в кольцах NOW/WAS; в «Показаниях» строка «Измеренный сдвиг … ± …″» рядом с «Прогноз каталога» | "Difference mode shows it moved — and SkyBlink measures the shift in arcseconds, with its error, checked against fixed stars." |
| 0:21–0:30 | Переключение en → ru → uz, телефон, кнопка «Я нашёл!», QR-код | "Three languages, any phone. Find a moving dot, leave a note for astronomers. Try it: [link]" |

Что НЕ говорить в видео (судья из IPAC проверит):
- не «−48 °C»: оценки температуры WISE 0855 около 250 K и выше, то есть примерно −20 °C или теплее;
- не «NOT IN GAIA — CANDIDATE» про WISE 0855: это известный объект (открыт в 2014). Честно: «известный коричневый карлик, в Gaia отсутствует»;
- не «102 канала по клику»: спектр собран из отдельных снимков, это предварительная оценка;
- не «вероятность 89%»: классификатора нет;
- цифры сдвига — только те, что приложение показало на реальных данных, с ошибкой; если ошибка большая, говорить «сдвиг виден», без числа.

---

## 3. Тексты для формы (черновики на английском — вставлять как есть, править факты)

### Project Name
**SkyBlink — Blink the Sky with SPHEREx**

### High-Level Project Summary (draft)
SkyBlink is a free web tool that lets anyone see how the sky changes over time in data from NASA's SPHEREx mission. Enter a star name or coordinates and SkyBlink fetches real SPHEREx spectral images from NASA/IPAC IRSA, stacks them by epoch, aligns them on a common sky grid, and plays them as a short "blink" animation, the same technique that discovered Pluto. A difference view makes moving objects pop out as black-and-white pairs, Gaia and CatWISE motion arrows show where known stars should move, and objects that move but have no confident catalog match are flagged as candidates to verify. SkyBlink compares epochs at matched wavelengths, because SPHEREx's linear variable filters make each pixel see a different wavelength. It works in English, Uzbek and Russian, on desktop and mobile, so more people can join citizen-science searches for brown dwarfs, comets and variable stars.

### Link to Project Demo
`<YouTube / Google Drive, публичная ссылка>`

### Link to Final Project
`<https://...vercel.app>` (+ GitHub в описании)

### Detailed Project Description (каркас — заполнить фактами в вс 18:00–20:00)
**What it does.** Search by name or coordinates → blink animation of SPHEREx epochs → difference view → catalog overlays (Gaia DR3, CatWISE2020) → click for a spectrum preview → light curve for variable stars → shareable/embeddable links (`?ra=&dec=&fov=&det=`).
**How it works.** Django REST backend queries IRSA SIA2 (`spherex_dr1`, `spherex_qr3`), downloads server-side cutouts, groups images into epochs (~6-month survey passes), keeps one detector at a time, computes the wavelength at the target for every image (LVF), masks bad pixels with FLAGS, inverse-variance stacks, reprojects to a shared TAN grid and renders PNG frames with one common brightness scale. Next.js + Aladin Lite frontend plays the frames and overlays catalogs. Popular targets are pre-computed so the demo is instant.
**Validated on** all five targets named in the challenge: Barnard's Star, Epsilon Indi B, WISE 0855−0714, RW Aurigae, R Draconis. `<вставить, что реально видно на каждом>`
**Honest limits.** SPHEREx has ~1.4 years of data, so nearby stars move only 1–2 pixels (6.15″/px); we add difference images, proper-motion arrows and a WISE comparison. Spectra and light curves are previews, not calibrated science products.
**Benefits / future.** Automatic candidate detection, more catalogs, community verification of findings, more languages.
**Tools.** Python (Django, DRF, astropy, astroquery, reproject, numpy, Pillow), TypeScript (Next.js, Tailwind, next-intl, zustand, Recharts), Aladin Lite v3, Vercel, Render/Railway, GitHub.

### NASA Data (обязательно, без этого нет глобальных наград)
- SPHEREx Level 2 Spectral Images, DR1 and QR3 (NASA/IPAC Infrared Science Archive, IRSA) — the core of every frame.
- IRSA SIA2 and cutout services; IRSA SPHEREx tutorial notebooks.
- WISE / unWISE and CatWISE2020 (NASA WISE/NEOWISE data via IRSA) — long-baseline comparison and motions of cold brown dwarfs. `<оставить, если реально используем>`
- SPHEREx HiPS / All-Sky products shown in Aladin Lite. `<оставить, если используем>`

### Space Agency Partner Data and Other References
- ESA Gaia DR3 (via VizieR / ESA archive) — proper motions. *(ESA — Space Agency Partner 2026)*
- CDS Strasbourg: Aladin Lite v3, SIMBAD/Sesame name resolver, VizieR.
- Libraries: astropy, astroquery, reproject, numpy, Pillow, Django, Django REST framework, Next.js, React, Tailwind CSS, next-intl, zustand, Recharts, lucide-react.
- Inspiration: WiseView and Backyard Worlds: Planet 9 (UX reference, no code reused).
- `<добавить всё, что реально подключили: шрифты, иконки, картинки>`

### Use of Super Intelligence (SI) (судьи это поле не видят, но отвечать честно)
We used SI tools as coding and research assistants: Claude (Anthropic) and ChatGPT (OpenAI) to read archive documentation, check data facts and review our plans; Gemini in Google Antigravity to help write and refactor code. The idea, product decisions, scientific checks and final review are ours. SI-assisted code is marked in the README and in file headers. `<если есть ИИ-картинки: "SI-generated images are watermarked">`

---

## 4. Таблица соответствия задаче (вставить в Detailed Description, повышает Relevance)

| Требование челленджа | Как SkyBlink его закрывает |
|---|---|
| Public-facing web tool for SPHEREx images | Next.js-сайт на Vercel, без регистрации |
| Enter RA/Dec, see a series of images like a video | Поиск по имени или координатам → blink-плеер |
| Test on Barnard's Star, ε Ind B, WISE 0855, RW Aur, R Dra | 5 пресетов на главной, все работают |
| Easy to update with new data releases | SIA2 по DR1 + QR3, кэш сбрасывается при новом релизе |
| Use the 102 bands creatively; stack per detector; spectra on the fly | Выбор детектора, стек внутри детектора, учёт длины волны (LVF), спектр по клику |
| Add or subtract epochs | Режимы Diff и Sum |
| Let users choose field of view | FOV 2′ / 5′ / 15′ / 30′ |
| Overlay Gaia / WISE | Стрелки Gaia DR3 и CatWISE, слои WISE в Aladin |
| Query by coordinates in the URL; embeddable | `/view?ra=&dec=&fov=&det=` и `/embed` |
| Display metadata such as contamination flags | Слой плохих пикселей + предупреждения |
| Use Astropy and Aladin | astropy/reproject на бэкенде, Aladin Lite на фронте |

---

## 5. Как помечать работу с ИИ (по правилам SI)

- **README:** раздел «Use of AI (SI) tools» с тем же текстом, что в форме.
- **Код:** в шапке файлов, где ИИ писал заметную часть, — строка `# Developed with SI assistance (Claude / ChatGPT / Gemini); reviewed by <name>`.
- **Изображения/видео:** если что-то сгенерировано — видимый водяной знак «SI-generated». Лучше обойтись без этого: только скриншоты нашего сайта и данных.
- **Идею** решения придумала команда; ИИ не должен быть автором идеи (так в правилах).

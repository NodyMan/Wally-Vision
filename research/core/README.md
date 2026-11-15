# research/core — spike для участника #1

`spike.py` проходит весь путь «SPHEREx → blink» одним скриптом: SIA2 (DR1 + QR3) → эпохи → вырезки → длина волны в точке цели → стек → общая сетка → GIF + diff.
Потом код переезжает в `backend/core/*` почти без изменений.

```bash
pip install astropy astroquery reproject numpy pillow

# 0. Офлайн-проверка (без интернета, ~1 с). Должна появиться пара «белое+чёрное» в центре *_diff.png
python research/core/spike.py --selftest

# 1. Настоящие данные (первый запуск 1–3 минуты: SIA2 ~9 с + ~24 вырезки по 4 МБ; повторный — секунды, из кэша)
python research/core/spike.py --target wise0855 --detector 6
python research/core/spike.py --target barnard  --detector 2
python research/core/spike.py --target rdra     --detector 2    # проверка фолбэка «бины по 30 дней»
python research/core/spike.py --ra 133.79513 --dec -7.24515 --detector 5 --fov 240

# 2. Сравнение эпох только на одной длине волны (LVF): оставить снимки, где λ в точке цели 4.6–4.8 мкм
python research/core/spike.py --target wise0855 --detector 6 --wl-min 4.6 --wl-max 4.8
```

В JSON у каждого кадра есть `target_wavelength_um` (медиана), `target_wavelength_range_um` и `target_bandwidth_um`. Если медианы эпох расходятся больше `--wl-tol` (0.05 мкм), скрипт пишет warning `wavelength_mismatch`: изменение яркости может быть спектральным, а не временным.

Результат: `research/core/out/` (GIF, diff PNG, кадры, JSON в формате `/api/blink`).
Кэш: `research/core/cache/` (или переменная `SKYBLINK_CACHE`). **Не коммитить** — добавить в `.gitignore`.

## Что проверено, а что нет
| Часть | Статус |
|---|---|
| SIA2 (колонки, `access_url`, скорость), формат cutout URL, слои FITS, пиксель 6.15″, «Server busy» | ✅ проверено живыми запросами к IRSA |
| Разбор CSV SIA2 и блокировка чужих URL | ✅ проверено на настоящей строке ответа SIA2 |
| Эпохи, стек, репроекция повёрнутых снимков, шкала, GIF, diff, метаданные длины волны | ✅ проверено `--selftest` |
| Чтение WCS-WAVE на реальном файле | ⏳ код как в туториале IRSA; если вернёт None — см. фолбэк в DATA_NOTES §0 |
| Ретрай на «Server busy» и выкидывание EPSF | ✅ проверено на имитации ответа |
| Полный прогон на реальных данных в Python | ⏳ **запустите первым делом** и допишите время в `docs/DATA_NOTES.md` |
| Биты `FLAGS` | ⏳ пока маскируется любой ненулевой флаг; если выкидывается > 50% пикселей, маска отключается с предупреждением |

## Что смотреть на результате
- Сдвиг за всю базу всего 1–2 пикселя (WISE 0855 ≈ 1.3, Barnard ≈ 1.9). На GIF он еле заметен, а на `*_diff.png` выглядит как пара белое + чёрное: белое — где объект сейчас, чёрное — где был.
- Если в `*_diff.png` светятся все звёзды подряд, значит, сетки не совпали (проверьте WCS) или у эпох разная длина волны (выберите другой детектор).

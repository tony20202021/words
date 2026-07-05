# Архитектура проекта

## Сервисы

| Компонент | Порт | Технологии | Назначение |
|-----------|------|-----------|------------|
| **Backend** | 8500 | FastAPI + MongoDB | Данные: слова, языки, пользователи, статистика |
| **BLS** | 8531 | FastAPI | Логика: сессии, карточки, графики, подсказки, QR |
| **Web Frontend** | 8548 | FastAPI + Jinja2 + HTMX | Веб-интерфейс |
| **Telegram Bot** | — | Python + aiogram 3.x | Telegram-фронтенд |
| **Android App** | — | Kotlin + Retrofit | Android-фронтенд |
| **MongoDB** | 8527 | — | База данных |

## Схема взаимодействия

```
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  Web Frontend    │  │  Telegram Bot    │  │  Android App     │
│  (порт 8548)     │  │  (aiogram 3.x)   │  │  (Kotlin)        │
└────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
         │                     │                      │
         │              HTTP/REST → BLS               │
         ▼                     ▼                      ▼
┌──────────────────────────────────────────────────────────────┐
│           BLS — Business Logic Service (порт 8531)           │
│  • Сессии изучения     • Построение карточек                 │
│  • Статистика + графики • Подсказки                          │
│  • Настройки            • Авторизация (одноразовые коды)     │
│  • GET /help, /version  • GET /qr (генерация QR-кодов)       │
└────────────────────────┬─────────────────────────────────────┘
                         │  HTTP/REST
                         ▼
          ┌──────────────────────────┐    ┌───────────┐
          │  Backend REST API (8500) │◄──►│  MongoDB  │
          │  Слова, языки, юзеры     │    │  (8527)  │
          └──────────────────────────┘    └───────────┘
```

Все фронтенды **stateless** — вся логика и состояние сессий хранится в BLS (in-memory dict).

---

## BLS — ключевые концепции

### Структура карточки (card_builder output)

```json
{
  "show_answer": false,
  "content": [{"type": "label|foreign|translation|transcription|hint|notice", "text": "..."}],
  "extra_content": [{"type": "label|extra", "text": "...", "group": "tones|references|radicals"}],
  "sounds": ["path/to/sound.mp3"],
  "buttons": [
    {"id": "know|show_answer|rate|reconsider|toggle_skip", "text": "...", "style": "...", "rating": "know|dont_know|null"}
  ],
  "big_word": {"word": "学", "transcription": "xué"},
  "meta": {
    "word_number": 42, "session_pos": 3, "session_total": 10,
    "words_studied": 42, "total_words": 500, "words_for_today": 10,
    "correct_count": 2, "incorrect_count": 1,
    "result_history": ["know", "dont_know", "know"],
    "pending_result": "know",
    "score_badge": {
      "text": "✓ знал · 7д", "variant": "success",
      "next_date": "2026-06-04",
      "new_next_date": "2026-06-11", "new_interval": 14, "new_variant": "success"
    },
    "hint_enabled_types": ["meaning", "phoneticsound"],
    "word_id": "..."
  }
}
```

Кнопка `toggle_skip` не включается если настройка `show_skip_button=False`.

### extra_content — порядок вывода

BLS отдаёт: тоны → ссылки → радикалы.  
Веб и Android переупорядочивают: **радикалы → ссылки → тоны**.  
Тоны и ссылки фильтруются по `[#N]` — скрываются слова с номером > `words_studied`.

### Жизненный цикл сессии

```
POST /session/start → {session_id, card}
                                │
            ┌───────────────────┼────────────────────┐
            ▼                   ▼                    ▼
POST /{sid}/know     POST /{sid}/show_answer   POST /{sid}/toggle_skip
  + bg: daily stats    + bg: finish stats
                        (first_finish + last_finish)
                                │
                        POST /{sid}/rate {rating: know|dont_know|skip}
                          + bg: daily stats
                                │
                    batch_exhausted=True → POST /{sid}/next_batch
                                            └── no_words=True → конец
```

После `know`/`rate`/`skip` BLS в фоне обновляет `daily` статистику.  
При каждом "не знаю" (`show_answer`) — обновляет `first_finish` и `last_finish` из `incorrect_count` сессии.

---

## Авторизация (одноразовые коды)

```
1. Любой фронтенд: POST /auth/mobile/create {user_id} → 6-символьный код (TTL 10 мин)
2. Целевой фронтенд: POST /auth/mobile/activate {code} → {user_id}
3. Защита: rate limit 20/min + блок кода после 3 неверных попыток на 60 сек
```

Веб: `GET /login?code=XXXXXX` — автовход по коду.  
Android: сохраняет user_id в SharedPreferences.

---

## QR-коды

`GET /qr?url=...` на BLS — PNG QR-код.  
Веб проксирует через `GET /qr?url=...` (браузер не имеет доступа к BLS напрямую).

QR генерируется для:
- Telegram `/web` — ссылка входа в веб
- Telegram `/android` — ссылка скачивания APK
- Веб `/connect` — ссылка входа с другого устройства
- Android «Код для веб» — QR в диалоге

---

## Android — структура

```
android/app/src/main/java/com/langbot/app/
├── LoginActivity.kt        — ввод BLS URL + кода авторизации
├── LanguagesActivity.kt    — список языков; проверка обновлений; «Код для веб» с QR
├── StudyActivity.kt        — карточка слова; pull-to-refresh
├── StatsActivity.kt        — статистика + 3 группы графиков; pull-to-refresh
├── SettingsActivity.kt     — настройки; pull-to-refresh
├── HintsActivity.kt        — управление подсказками
├── HelpActivity.kt         — справка (GET /help)
└── network/
    ├── BLSService.kt       — Retrofit API
    └── ApiModels.kt        — data-классы
```

---

## Статистика и графики

Типы дневной статистики в БД:
- `daily` — обновляется после каждого ответа (фоновая задача `_bg_update_daily`)
- `first_finish` — максимум ошибок за день; обновляется при каждом "не знаю" если новое значение больше сохранённого
- `last_finish` — текущее количество ошибок; перезаписывается при каждом "не знаю"

Поля `first_finish` / `last_finish`:
- `words_unknown` — количество ошибок из сессии (`incorrect_count`), хранится напрямую
- Триггер: `show_answer` endpoint → `_bg_update_finish_on_unknown`
- Старые записи (до 3.0.37): `words_unknown` вычисляется из `words_studied - words_known - words_skipped`

Три группы графиков:
1. **Распределение слов** (today): words_for_today, words_unknown, check_interval
2. **Прогресс за месяц** (monthly recent, 30 дней)
3. **Прогресс за всё время** (monthly all)

---

## Общие модули (`common/`)

| Файл | Назначение |
|------|-----------|
| `common/version.py` | Единая версия (`"3.0.26"`); `versionCode = major*10000 + minor*100 + patch` |
| `common/help_text.py` | Текст справки — единый для всех платформ |

При любом изменении кода — инкрементировать patch в `common/version.py` и `android/app/build.gradle`.

---

## Запуск сервисов (systemd)

```bash
sudo systemctl start|stop|restart|status langbot-backend
sudo systemctl start|stop|restart|status langbot-bls
sudo systemctl start|stop|restart|status langbot-web
sudo systemctl start|stop|restart|status langbot-telegram
```

Автоперезапуск при изменении `.py`/`.html` в `app/` и `../common/`.

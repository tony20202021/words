# Архитектура проекта

## Сервисы

| Компонент | Порт | Технологии | Назначение |
|-----------|------|-----------|------------|
| **Backend** | 8500 | FastAPI + MongoDB | Данные: слова, языки, пользователи, статистика |
| **BLS** | 8700 | FastAPI | Логика: сессии, карточки, графики, подсказки |
| **Web Frontend** | 8800 | FastAPI + Jinja2 + HTMX | Веб-интерфейс |
| **Telegram Bot** | — | Python + aiogram 3.x | Telegram-фронтенд |
| **Android App** | — | Kotlin + Retrofit | Android-фронтенд |
| **MongoDB** | 27017 | — | База данных |

## Схема взаимодействия

```
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  Web Frontend    │  │  Telegram Bot    │  │  Android App     │
│  (порт 8800)     │  │  (aiogram 3.x)   │  │  (Kotlin)        │
└────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
         │                     │                      │
         │              HTTP/REST → BLS               │
         ▼                     ▼                      ▼
┌──────────────────────────────────────────────────────────────┐
│           BLS — Business Logic Service (порт 8700)           │
│  • Сессии изучения     • Построение карточек                 │
│  • Статистика + графики • Подсказки                          │
│  • Настройки            • Аутентификация (мобильный код)     │
│  • GET /help            (общий текст справки)                │
└────────────────────────────┬─────────────────────────────────┘
                             │  HTTP/REST
                             ▼
              ┌──────────────────────────┐    ┌───────────┐
              │  Backend REST API (8500) │◄──►│  MongoDB  │
              │  Слова, языки, юзеры     │    │  (27017)  │
              └──────────────────────────┘    └───────────┘
```

Все фронтенды **stateless** — вся логика и состояние сессий хранится в BLS (in-memory dict).

---

## BLS — ключевые концепции

### Структура карточки (card_builder output)

```json
{
  "show_answer": false,
  "content": [
    {"type": "label|foreign|translation|transcription|hint|notice", "text": "..."}
  ],
  "extra_content": [
    {"type": "label|extra", "text": "...", "group": "tones|references|radicals"}
  ],
  "sounds": ["path/to/sound.mp3"],
  "buttons": [
    {"id": "know|show_answer|rate|reconsider|toggle_skip", "text": "...", "style": "success|outline-danger|outline-secondary", "rating": "know|dont_know|null"}
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
      "new_next_date": "2026-06-11", "new_interval": 14
    },
    "hint_enabled_types": ["meaning", "phoneticsound"],
    "word_id": "..."
  }
}
```

### extra_content — порядок вывода

BLS отправляет: тоны → ссылки → радикалы.  
Веб и Android показывают в порядке: **радикалы → ссылки → тоны** (переупорядочивают на клиенте).  
Telegram — в порядке BLS.

Радикалы (`group="radicals"`) — plain text с деревом Unicode-символами, пробелы значимы.  
Ссылки и тоны (`group="references"`, `"tones"`) — HTML с `<b>`, `<i>`.

### Жизненный цикл сессии

```
POST /session/start → {session_id, card}
                                │
            ┌───────────────────┼────────────────────┐
            ▼                   ▼                    ▼
POST /{sid}/know     POST /{sid}/show_answer   POST /{sid}/toggle_skip
            │                   │
            │           POST /{sid}/rate {rating: know|dont_know}
            │                   │
            └──── batch_exhausted=True → POST /{sid}/next_batch
                                          └── no_words=True → конец
```

### score_badge — логика

После нажатия "Знаю"/"Показать ответ" слово обновляется в БД **до** отрисовки.  
Чтобы бейдж показывал состояние ДО ответа, `session_service` сохраняет старые значения в сессию:

```python
session["prev_score"] = old_score
session["prev_interval"] = old_interval
session["prev_next_check_date"] = old_date
```

`card_builder` использует `prev_*` при `show_answer=True`.

---

## Авторизация Android

```
1. Telegram: /connect_android → POST /auth/mobile/create {user_id} → 6-символьный код (TTL 10 мин)
2. Android: пользователь вводит код → POST /auth/mobile/activate {code} → {user_id}
3. Android: сохраняет user_id в SharedPreferences, использует для всех BLS-запросов
```

---

## Общие модули (`common/`)

| Файл | Назначение |
|------|-----------|
| `common/version.py` | Единая версия всего проекта (строка `"3.0.9"`) |
| `common/help_text.py` | Текст справки — единый для всех платформ; BLS отдаёт через `GET /help` |

### Правило версионирования

При **любом** изменении кода — инкрементировать patch в `common/version.py` и `android/app/build.gradle`.  
`versionCode` = `major*10000 + minor*100 + patch` (напр. 3.0.9 → 30009).

---

## Android — структура

```
android/app/src/main/java/com/langbot/app/
├── LoginActivity.kt        — ввод кода, инициализация BLSClient
├── LanguagesActivity.kt    — список языков + меню (Помощь, Веб, Telegram, Выйти)
├── StudyActivity.kt        — карточка слова (основная активность)
│     Меню: ↺ Обновить | 📊 Статистика | 🔄 Начать заново
├── StatsActivity.kt        — статистика + графики
├── SettingsActivity.kt     — настройки (toggles + числовые)
├── HintsActivity.kt        — управление подсказками (CRUD)
├── HelpActivity.kt         — справка (загружает из BLS GET /help)
└── network/
    ├── BLSService.kt       — Retrofit API-интерфейс
    └── ApiModels.kt        — data-классы
```

---

## Ключевые файлы

| Файл | Назначение |
|------|-----------|
| `business_logic_service/app/services/card_builder.py` | Сборка карточки: контент, кнопки, бейдж, big_word, extra_content |
| `business_logic_service/app/services/session_service.py` | Управление сессией: know/show_answer/rate/reconsider/toggle_skip |
| `business_logic_service/app/routers/info.py` | GET /help — текст справки из common/help_text.py |
| `telegram_bot/app/bot/handlers/study.py` | /study (продолжить), /restart (начать заново), _display_card |
| `telegram_bot/app/bot/handlers/start.py` | /start, выбор языка, study_start (через кнопку «Начать заново») |
| `telegram_bot/app/bot/handlers/settings.py` | Настройки: SETTING_LABELS, NUMERIC_LABELS, skip_marked — state-dependent label |
| `web_frontend/app/templating.py` | Единый Jinja2-инстанс с globals: app_version, telegram_bot_url |
| `web_frontend/app/templates/base.html` | Navbar с ссылками 🤖 📱, версия, меню |

---

## Запуск сервисов (systemd)

```bash
sudo systemctl start|stop|restart|status langbot-backend
sudo systemctl start|stop|restart|status langbot-bls
sudo systemctl start|stop|restart|status langbot-web
sudo systemctl start|stop|restart|status langbot-telegram
```

Автоперезапуск при изменении `.py` файлов — через `watchmedo auto-restart` (BLS и Telegram Bot).

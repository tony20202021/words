# Архитектура: декомпозиция сервисов

## Схема взаимодействия

```
Telegram Bot (frontend/, старый)   ──HTTP──┐
                                           │
Telegram Bot (telegram_bot/, новый) ──HTTP─┤──► Business Logic Service (BLS, :8531)
                                           │              │
Web Frontend (:8548) ──────────────HTTP────┘              ▼
                                                   Backend API (:8500)
                                                          │
                                                          ▼
                                                     MongoDB (:8527)
```

## Сервисы

| Сервис | Порт | Директория | Запуск |
|--------|------|------------|--------|
| MongoDB | 8527 | — | `start_1_db.sh` |
| Backend API | 8500 | `backend/` | `start_2_backend.sh` |
| Business Logic Service | 8531 | `business_logic_service/` | `start_4_bls.sh` |
| Web Frontend | 8548 | `web_frontend/` | `start_5_web.sh` |
| Telegram Bot (старый) | — | `frontend/` | `start_3_frontend_auto_reload.sh` |
| Telegram Bot (новый) | — | `telegram_bot/` | `start_6_telegram_bot.sh` |

## Принцип разделения

**BLS — единственное место с логикой отображения.**

- `card_builder.py` строит карточку слова: что показывать, какие кнопки
- Web Frontend и Telegram Bot только рендерят полученную карточку
- Клиенты не содержат логики выбора контента

### Структура `card`

```json
{
  "show_answer": false,
  "content": [
    {"type": "label|foreign|translation|transcription|hint|notice", "text": "...", "align": "center"}
  ],
  "extra_content": [
    {"type": "label|extra", "text": "...", "group": "radicals|references|tones"}
  ],
  "sounds": ["sounds/path.mp3"],
  "buttons": [
    {"id": "know|show_answer|rate|toggle_skip|reconsider", "text": "...", "style": "...", "rating": "know|dont_know"}
  ],
  "big_word": {"word": "你好", "transcription": "nǐ hǎo"},
  "meta": {
    "word_number": 5,
    "score": -1,
    "interval": 0,
    "next_check_date": "",
    "is_skipped": false,
    "session_pos": 1,
    "session_total": 51,
    "correct_count": 0,
    "incorrect_count": 0,
    "result_history": ["know", "dont_know"],
    "pending_result": null,
    "words_studied": 1000,
    "total_words": 9935,
    "words_for_today": 51,
    "language_name_ru": "Китайский",
    "language_name_foreign": "中文",
    "score_badge": {
      "text": "новое",
      "variant": "secondary|success|danger",
      "next_date": "",
      "new_interval": 32,
      "new_next_date": "2026-06-27",
      "new_variant": "success|danger|secondary"
    }
  }
}
```

**`extra_content`** — дополнительные блоки (радикалы, ссылки, тоны); клиент сортирует по группам: `radicals → references → tones`. Показывается только после ответа.

**`score_badge`** — всегда отражает состояние **до** ответа (`prev_score`). Поля `new_interval`, `new_next_date`, `new_variant` появляются только при `show_answer=true` и `interval>0`, отражая новое расписание повтора. Цвет `new_variant` определяется **новым** score (не предыдущим).

**`pending_result`** — `"know"` или `"dont_know"` пока идёт анимация перехода к следующему слову; `null` до нажатия кнопки.

## Авторизация в Web Frontend

### По Telegram ID (с подтверждением)
```
Web: POST /auth/lookup {telegram_id}
  → BLS находит пользователя → создаёт токен → шлёт сообщение в Telegram
  → Web показывает экран ожидания (HTMX polling GET /auth/poll?token=T каждые 2с)
  → Бот нажимает Да → BLS POST /auth/confirm/{token}
  → Web получает confirmed → сохраняет сессию
```

### По имени (без Telegram)
```
Web: POST /auth/lookup {name}
  → BLS ищет пользователя по first_name
  → Если найден: возвращает user_id → Web сразу логинит
```

### Прямая ссылка из бота
```
Бот отправляет: http://<host>:8548/autologin?telegram_id=<id>
Web: GET /autologin → lookup → login → redirect /languages
```

### Если пользователь не найден
Web предлагает создать нового:
- Telegram: вводит имя → BLS создаёт + шлёт Telegram подтверждение
- Имя: BLS создаёт с генерированным telegram_id

# Архитектура: декомпозиция сервисов

## Схема взаимодействия

```
Telegram Bot (frontend/, старый)   ──HTTP──┐
                                           │
Telegram Bot (telegram_bot/, новый) ──HTTP─┤──► Business Logic Service (BLS, :8700)
                                           │              │
Web Frontend (:8800) ──────────────HTTP────┘              ▼
                                                   Backend API (:8500)
                                                          │
                                                          ▼
                                                     MongoDB (:27027)
```

## Сервисы

| Сервис | Порт | Директория | Запуск |
|--------|------|------------|--------|
| MongoDB | 27027 | — | `start_1_db.sh` |
| Backend API | 8500 | `backend/` | `start_2_backend.sh` |
| Business Logic Service | 8700 | `business_logic_service/` | `start_4_bls.sh` |
| Web Frontend | 8800 | `web_frontend/` | `start_5_web.sh` |
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
  "content": [{"type": "label|foreign|translation|transcription|hint|notice", "text": "..."}],
  "sounds": ["sounds/path.mp3"],
  "buttons": [{"id": "know|show_answer|rate|toggle_skip|reconsider", "text": "...", "style": "...", "rating": "know|dont_know"}],
  "meta": {
    "word_number": 5, "score": -1, "session_pos": 1,
    "correct_count": 0, "incorrect_count": 0,
    "score_badge": {"text": "новое", "variant": "secondary"}
  }
}
```

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
Бот отправляет: http://<host>:8800/autologin?telegram_id=<id>
Web: GET /autologin → lookup → login → redirect /languages
```

### Если пользователь не найден
Web предлагает создать нового:
- Telegram: вводит имя → BLS создаёт + шлёт Telegram подтверждение
- Имя: BLS создаёт с генерированным telegram_id

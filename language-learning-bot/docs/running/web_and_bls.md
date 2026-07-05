# Запуск BLS и Web Frontend

## Порядок запуска

```
1. MongoDB      (start_1_db.sh)
2. Backend API  (start_2_backend.sh)
3. BLS          (start_4_bls.sh)        ← новый
4. Web Frontend (start_5_web.sh)        ← новый
5. Telegram Bot (start_6_telegram_bot.sh или start_3_frontend_auto_reload.sh)
```

## BLS (Business Logic Service) — порт 8531

```bash
# Запуск вручную:
./start_4_bls.sh

# Или напрямую:
cd business_logic_service
BACKEND_URL=http://localhost:8573 \
TELEGRAM_BOT_TOKEN=<token> \
conda run -n amikhalev_language_learning_bot \
    uvicorn app.main:app --host 0.0.0.0 --port 8531

# Проверка:
curl http://localhost:8531/health
```

**Переменные окружения:**

| Переменная | По умолчанию | Описание |
|-----------|-------------|----------|
| `BACKEND_URL` | `http://localhost:8573` | URL Backend API |
| `TELEGRAM_BOT_TOKEN` | пусто | Для отправки auth-сообщений в Telegram |

## Web Frontend — порт 8548

```bash
# Запуск вручную:
./start_5_web.sh

# Или напрямую:
cd web_frontend
BLS_URL=http://localhost:8531 \
SECRET_KEY=<секретный_ключ> \
WEB_URL=http://136.244.102.39:8548 \
conda run -n amikhalev_language_learning_bot \
    uvicorn app.main:app --host 0.0.0.0 --port 8548

# Проверка:
curl http://localhost:8548/health
```

**Переменные окружения:**

| Переменная | По умолчанию | Описание |
|-----------|-------------|----------|
| `BLS_URL` | `http://localhost:8531` | URL BLS |
| `BACKEND_URL` | `http://localhost:8573` | URL Backend (для proxy звуков) |
| `SECRET_KEY` | `change-me-in-production-please` | Ключ подписи сессионных cookie |
| `WEB_URL` | `http://localhost:8548` | Публичный URL сайта (для ссылок из бота) |

## Новый Telegram Bot — порт не нужен

```bash
./start_6_telegram_bot.sh

# Переменные:
BOT_TOKEN=<токен_бота>
BLS_URL=http://localhost:8531
```

## systemd-сервисы (без авто-запуска)

Файлы сервисов находятся в `deploy/`:

```bash
# Установить (скопировать):
sudo cp deploy/langbot-bls.service /etc/systemd/system/
sudo cp deploy/langbot-web.service /etc/systemd/system/
sudo cp deploy/langbot-telegram.service /etc/systemd/system/
sudo systemctl daemon-reload

# Настроить переменные — скопировать .env.example в .env и заполнить:
cp deploy/.env.example deploy/.env
nano deploy/.env

# Запустить вручную (без auto-start):
sudo systemctl start langbot-bls
sudo systemctl start langbot-web

# Включить авто-запуск (опционально):
sudo systemctl enable langbot-bls langbot-web
```

## Автоперезапуск при изменениях

Web Frontend и BLS запускаются через `watchmedo auto-restart` — изменения применяются автоматически:

| Файл | Web Frontend | BLS |
|------|-------------|-----|
| `.py` | ✅ перезапуск | ✅ перезапуск |
| `.html` | ✅ перезапуск | — |

Скрипты watchmedo:
- Web: `start_web_auto_reload.sh` — наблюдает `app/**/*.py` и `app/**/*.html`
- BLS: `start_bls_auto_reload.sh` — наблюдает `app/**/*.py`

**Сессии BLS**: хранятся in-memory — после рестарта BLS нужно открыть страницу учёбы заново.

## Страница статистики (/stats)

Показывает для каждого языка:

- Счётчики: изучено, знаю, всего, прогресс %
- Прогресс известно/изучено (%), пропущено
- Значок «к повторению» если есть слова на сегодня
- Кнопка «📊 Графики» — разворачивает три блока:
  - **Распределение слов** — 3 графика текущего состояния
  - **Прогресс за месяц** — последние 30 дней
  - **Прогресс за все время** — весь архив

Графики подгружаются лениво при первом раскрытии блока (через `data-src` + Bootstrap `show.bs.collapse` событие).

### Маршруты графиков (web frontend → BLS)

| Web Frontend | BLS |
|---|---|
| `GET /stats/chart/{lang_id}/{chart_name}` | `GET /statistics/{uid}/{lang_id}/chart/{chart_name}` |
| `GET /stats/monthly-chart/{lang_id}/{chart_name}` | `GET /statistics/{uid}/{lang_id}/monthly-chart/{chart_name}?show_all=true` |
| `GET /stats/monthly-chart-recent/{lang_id}/{chart_name}` | `GET /statistics/{uid}/{lang_id}/monthly-chart/{chart_name}?show_all=false` |

Доступные имена графиков: `words_for_today`, `words_unknown`, `check_interval`, `words_studied`, `words_new`, `words_known`, `words_unknown_before`, `words_unknown_after`.

## Прогресс-бар в сессии учёбы

Полоса прогресса в карточке слова:

- **Знаменатель** — `words_for_today` из статистики (точное число слов на сегодня); при старте новых слов — `session_total` из батча
- **Сегменты** — зелёный (`know`), красный (`dont_know`), серый (`skip`) по `result_history`
- **Анимированный сегмент** (`pending_result`) — появляется сразу после нажатия «Знаю» или «Не знаю», до перехода к следующему слову

### Поведение reconsider («Ой, все-таки не знаю»)

После нажатия «Ой, все-таки не знаю» BLS автоматически вызывает `rate_word("dont_know")` — лишний шаг «Дальше» не нужен, переход к следующему слову происходит сразу.

## Проверка работы

```bash
# Здоровье всех сервисов:
curl http://localhost:8531/health   # BLS
curl http://localhost:8548/health   # Web

# Тесты:
cd business_logic_service
conda run -n amikhalev_language_learning_bot pytest tests/ -v

cd web_frontend
conda run -n amikhalev_language_learning_bot pytest tests/ -v

cd telegram_bot
conda run -n amikhalev_language_learning_bot pytest tests/ -v
```

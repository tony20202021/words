# Автозапуск Language Learning Bot через systemd

## Содержание
1. [Обзор](#обзор)
2. [Создание сервисных файлов](#создание-сервисных-файлов)
   - [langbot-db.service](#langbot-dbservice)
   - [langbot-backend.service](#langbot-backendservice)
   - [langbot-frontend.service](#langbot-frontendservice)
3. [Активация и запуск](#активация-и-запуск)
4. [Управление сервисами](#управление-сервисами)
5. [Просмотр логов](#просмотр-логов)
6. [Устранение неполадок](#устранение-неполадок)
7. [Удаление сервисов](#удаление-сервисов)

---

## Обзор

Systemd позволяет автоматически запускать все компоненты бота при старте сервера, перезапускать их при сбоях и управлять ими через единый интерфейс `systemctl`.

**Зависимости при запуске:**
```
langbot-db  →  langbot-backend  →  langbot-frontend
```

**Важные параметры окружения:**
- Пользователь: `tony`
- Рабочая директория: `/home/tony/repos/words/language-learning-bot`
- Conda-окружение: `amikhalev_language_learning_bot`
- Python: `/home/tony/miniconda3/envs/amikhalev_language_learning_bot/bin/python`

---

## Создание сервисных файлов

### langbot-db.service

MongoDB запускается с флагом `--fork` и уходит в фон сама — поэтому используется `Type=forking`.

```bash
sudo nano /etc/systemd/system/langbot-db.service
```

```ini
[Unit]
Description=Language Bot - MongoDB
After=network.target

[Service]
Type=forking
User=tony
WorkingDirectory=/home/tony/repos/words/language-learning-bot
Environment="PATH=/home/tony/miniconda3/envs/amikhalev_language_learning_bot/bin:/home/tony/miniconda3/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/bin/bash start_1___db.sh__
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

### langbot-backend.service

Бэкенд работает на переднем плане (`Type=simple`). Запускается только после успешного старта БД.

```bash
sudo nano /etc/systemd/system/langbot-backend.service
```

```ini
[Unit]
Description=Language Bot - Backend API
After=langbot-db.service
Requires=langbot-db.service

[Service]
Type=simple
User=tony
WorkingDirectory=/home/tony/repos/words/language-learning-bot
Environment="PATH=/home/tony/miniconda3/envs/amikhalev_language_learning_bot/bin:/home/tony/miniconda3/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/bin/bash start_2___backend.sh__
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

### langbot-frontend.service

Фронтенд (Telegram-бот) запускается последним — после бэкенда.

```bash
sudo nano /etc/systemd/system/langbot-frontend.service
```

```ini
[Unit]
Description=Language Bot - Frontend (Telegram Bot)
After=langbot-backend.service
Requires=langbot-backend.service

[Service]
Type=simple
User=tony
WorkingDirectory=/home/tony/repos/words/language-learning-bot
Environment="PATH=/home/tony/miniconda3/envs/amikhalev_language_learning_bot/bin:/home/tony/miniconda3/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/bin/bash start_3_frontend_auto___reload.sh__
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## Активация и запуск

### Первый запуск

```bash
# Перечитать конфигурацию systemd
sudo systemctl daemon-reload

# Включить автозапуск при перезагрузке
sudo systemctl enable langbot-db langbot-backend langbot-frontend

# Запустить все сервисы
sudo systemctl start langbot-db
sleep 5
sudo systemctl start langbot-backend
sleep 5
sudo systemctl start langbot-frontend
```

### Проверка статуса после запуска

```bash
sudo systemctl status langbot-db langbot-backend langbot-frontend
```

Ожидаемый вывод для каждого сервиса:
```
● langbot-backend.service - Language Bot - Backend API
     Loaded: loaded (/etc/systemd/system/langbot-backend.service; enabled)
     Active: active (running) since ...
```

---

## Управление сервисами

### Запуск / Остановка / Перезапуск

```bash
# Запустить отдельный сервис
sudo systemctl start langbot-db

# Остановить отдельный сервис
sudo systemctl stop langbot-frontend

# Перезапустить сервис (например, после изменения кода)
sudo systemctl restart langbot-backend

# Перезапустить все сразу
sudo systemctl restart langbot-db langbot-backend langbot-frontend
```

### Включить / Отключить автозапуск

```bash
# Включить автозапуск при перезагрузке сервера
sudo systemctl enable langbot-db langbot-backend langbot-frontend

# Отключить автозапуск (сервисы останутся запущенными сейчас, но не стартуют при ребуте)
sudo systemctl disable langbot-db langbot-backend langbot-frontend
```

### Проверка состояния

```bash
# Краткий статус всех трёх сервисов
sudo systemctl status langbot-db langbot-backend langbot-frontend

# Показать только активен / не активен
systemctl is-active langbot-db
systemctl is-active langbot-backend
systemctl is-active langbot-frontend
```

### Перезапуск после изменений в .service файлах

Если вносились правки в сам `.service` файл — нужно перечитать конфигурацию:

```bash
sudo systemctl daemon-reload
sudo systemctl restart langbot-backend  # или нужный сервис
```

---

## Просмотр логов

Все логи systemd хранятся в journald и доступны через `journalctl`.

```bash
# Последние 50 строк конкретного сервиса
sudo journalctl -u langbot-db -n 50 --no-pager
sudo journalctl -u langbot-backend -n 50 --no-pager
sudo journalctl -u langbot-frontend -n 50 --no-pager

# Следить за логами в реальном времени (аналог tail -f)
sudo journalctl -u langbot-frontend -f

# Логи за последний час
sudo journalctl -u langbot-backend --since "1 hour ago"

# Логи с конкретного момента
sudo journalctl -u langbot-backend --since "2024-01-15 10:00:00"

# Логи всех трёх сервисов вместе
sudo journalctl -u langbot-db -u langbot-backend -u langbot-frontend -f
```

> **Совет**: При проблемах с запуском всегда смотрите логи того сервиса, который упал:
> ```bash
> sudo journalctl -u langbot-backend -n 100 --no-pager
> ```

---

## Устранение неполадок

### Сервис не запускается

```bash
# Шаг 1 — посмотреть статус и последнее сообщение об ошибке
sudo systemctl status langbot-backend

# Шаг 2 — посмотреть полные логи
sudo journalctl -u langbot-backend -n 100 --no-pager

# Шаг 3 — попробовать запустить скрипт вручную от имени tony
sudo -u tony bash -c 'cd /home/tony/repos/words/language-learning-bot && \
  PATH=/home/tony/miniconda3/envs/amikhalev_language_learning_bot/bin:$PATH \
  bash start_2___backend.sh__'
```

### MongoDB не запускается (langbot-db)

```bash
# Проверить логи MongoDB напрямую
cat ~/mongodb/log/mongod.log

# Проверить, не занят ли порт
lsof -i :27017

# Проверить, что директории существуют
ls -la ~/mongodb/data ~/mongodb/log
```

### Бэкенд падает сразу после старта

Возможные причины:
- MongoDB ещё не успела подняться — увеличьте `RestartSec` в `langbot-backend.service` до 15 секунд
- Порт 8500 уже занят: `lsof -i :8500`
- Ошибка в конфигурации Hydra: `cat backend/logs/backend.log`

### Фронтенд завершается с ошибкой "Conflict: terminated by other getUpdates"

Работает несколько экземпляров Telegram-бота одновременно:

```bash
# Найти все процессы фронтенда
ps aux | grep -e "frontend" -e "watch_and_reload"

# Завершить все
pkill -f "watch_and_reload.py"
pkill -f -- "--process-name=frontend"

# Подождать 30 секунд и перезапустить
sleep 30
sudo systemctl start langbot-frontend
```

### Проверка всех процессов бота

```bash
ps aux | grep -e "mongod" \
         -e "process-name=backend" \
         -e "process-name=frontend" \
         -e "watch_and_reload" \
  | grep -v grep
```

---

## Удаление сервисов

Если нужно полностью убрать автозапуск:

```bash
# Остановить сервисы
sudo systemctl stop langbot-frontend langbot-backend langbot-db

# Отключить автозапуск
sudo systemctl disable langbot-frontend langbot-backend langbot-db

# Удалить файлы сервисов
sudo rm /etc/systemd/system/langbot-db.service
sudo rm /etc/systemd/system/langbot-backend.service
sudo rm /etc/systemd/system/langbot-frontend.service

# Перечитать конфигурацию
sudo systemctl daemon-reload
```

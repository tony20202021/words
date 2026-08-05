# Установка Language Learning Bot

Развёртывание с нуля. Боевая установка — сервер **i-04** (`77.81.226.56`),
сервисы под systemd.

## Требования

| Что | Версия | Зачем |
|-----|--------|-------|
| Python | 3.10+ | все сервисы |
| MongoDB | 7.0 | единственная БД проекта |
| JDK | **17** | сборка Android (AGP 8.2 / Gradle 8.4) |
| Android SDK | platform 34, build-tools 34.0.0 | сборка APK |
| nginx | 1.24+ | терминация TLS |

Железа хватает скромного: i-04 — 2 vCPU / 3.8 GiB RAM. GPU не нужен.

## 1. Окружение Python

```bash
conda env create -f environment.yml
conda activate amikhalev_language_learning_bot
pip install -r requirements.txt
```

Подробнее: [environment_setup.md](environment_setup.md)

## 2. MongoDB

Проект слушает нестандартный порт **8527**. На i-04 стоит пользовательская установка
в `~/mongodb` (без root), поднимается юнитом `langbot-db`.

Установка и настройка: [mongodb_setup.md](mongodb_setup.md)

## 3. Переменные окружения

```bash
cp .env.example .env
```

Обязательный минимум:

```env
MONGODB_URL=mongodb://localhost:8527
MONGODB_DB_NAME=language_learning_bot
BLS_PUBLIC_URL=https://<ip>:8443
WEB_URL=http://<ip>:8548
BOT_TOKEN=<токен от @BotFather>
SECRET_KEY=<случайная строка>
TELEGRAM_BOT_URL=https://t.me/<имя бота>
```

> ⚠️ `WEB_URL` задавать обязательно. Без него срабатывает хардкод-дефолт в коде,
> и команды `/web` и `/android` начнут отправлять пользователей не на тот сервер.

`.env` в git не попадает — он в `.gitignore`.

## 4. Инициализация базы

```bash
python scripts/init_db.py
python scripts/db_indexes.py
```

## 5. Запуск

В проде — systemd:

```bash
sudo systemctl enable --now langbot-db langbot-backend langbot-bls langbot-web langbot-telegram
```

Вручную для разработки:

```bash
./start_1_db.sh            # MongoDB      :8527
./start_2_backend.sh       # Backend API  :8573
./start_4_bls.sh           # BLS          :8531
./start_5_web.sh           # Web          :8548
./start_6_telegram_bot.sh  # Telegram-бот
```

Подробнее: [../running/running_guide.md](../running/running_guide.md),
[../running/systemctl_guide.md](../running/systemctl_guide.md)

## 6. TLS

Порт 443 занят посторонним сервисом, поэтому TLS вынесен на **8443** (BLS) и
**8444** (web). Сертификат Let's Encrypt выписан на IP-адрес — домен не нужен.

Схема и подводные камни (порт 80 под ACME-челлендж, перезагрузка nginx после
продления сертификата): [../architecture.md](../architecture.md)

## 7. Проверка

```bash
curl -s localhost:8573/api/health    # backend
curl -s localhost:8531/health        # BLS
curl -s localhost:8531/version       # версия проекта
curl -s -o /dev/null -w '%{http_code}\n' localhost:8548/
```

Функциональная проверка — отправить боту `/start` в Telegram.

## Типичные проблемы

**Порт занят**

```bash
ss -ltnp | grep -E '8527|8531|8548|8573'
```

**Сервис не поднимается**

```bash
systemctl status langbot-<имя>
journalctl -u langbot-<имя> -n 50
```

**Бот не отвечает.** Убедитесь, что тем же токеном не запущен второй экземпляр:

```bash
curl -s "https://api.telegram.org/bot$BOT_TOKEN/getWebhookInfo"
```

Непустой `last_error_message` с упоминанием конфликта означает, что бот поллит
дважды — Telegram отдаёт обновления только одному экземпляру.

## Тесты

```bash
python run_tests.sh                        # bls, telegram, web, backend, common
cd android && ./gradlew testDebugUnitTest  # Android, эмулятор не нужен
```

Подробнее: [../development/testing_guide.md](../development/testing_guide.md)

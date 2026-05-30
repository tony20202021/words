# Language Learning Bot

Система для изучения иностранных слов с интервальным повторением.  
Версия: **3.0.9** — единая для всех компонентов (`common/version.py`).

---

## Платформы

| Платформа | Технологии | Адрес / запуск |
|-----------|-----------|----------------|
| **Telegram-бот** | Python + aiogram 3.x | [@language_learning_words_bot](https://t.me/language_learning_words_bot) |
| **Веб-приложение** | FastAPI + Jinja2 + HTMX | порт 8800 |
| **Android** | Kotlin + Retrofit | `android/LangBot.apk` |
| **BLS** | FastAPI (логика) | порт 8700 |
| **Backend** | FastAPI + MongoDB | порт 8500 |

Все фронтенды stateless — вся логика и состояние сессий в BLS.

---

## Архитектура

```
Telegram Bot ──┐
Web Frontend   ├──► BLS (порт 8700) ──► Backend (порт 8500) ──► MongoDB
Android App  ──┘      (сессии, карточки,                       (порт 27017)
                        статистика, подсказки)
```

Подробнее: [`docs/architecture.md`](docs/architecture.md)

---

## Быстрый старт

### Требования
- Python 3.10+ (conda env `amikhalev_language_learning_bot`)
- MongoDB 5.0+
- JDK 8+ и Android SDK (для сборки APK)

### Запуск сервисов

```bash
sudo systemctl start langbot-backend   # порт 8500
sudo systemctl start langbot-bls       # порт 8700
sudo systemctl start langbot-web       # порт 8800
sudo systemctl start langbot-telegram  # Telegram-бот
```

### Переменные окружения (`.env`)

```env
MONGODB_URL=mongodb://localhost:27027
MONGODB_DB_NAME=language_learning_bot
BACKEND_URL=http://localhost:8500
BLS_URL=http://localhost:8700
BOT_TOKEN=...
SECRET_KEY=...
TELEGRAM_BOT_URL=https://t.me/...
BLS_PUBLIC_URL=http://<external-ip>:8700
```

### Сборка Android APK

```bash
cd android
export ANDROID_SDK_ROOT=/home/tony/Android/Sdk
./gradlew assembleDebug
# APK: app/build/outputs/apk/debug/app-debug.apk
cp app/build/outputs/apk/debug/app-debug.apk LangBot.apk
```

---

## Команды Telegram-бота

| Команда | Описание |
|---------|----------|
| `/start` | Главное меню, выбор языка |
| `/study` | Продолжить текущую сессию |
| `/restart` | Начать заново (сброс сессии) |
| `/language` | Сменить язык |
| `/settings` | Настройки процесса обучения |
| `/stats` | Статистика по текущему языку |
| `/web` | Открыть веб-версию |
| `/android` | Скачать Android-приложение |
| `/connect_android` | Код для входа в Android-приложение |
| `/help` | Справка |

---

## Структура проекта

```
language-learning-bot/
├── backend/                # REST API + MongoDB (порт 8500)
├── business_logic_service/ # BLS — логика и сессии (порт 8700)
├── telegram_bot/           # Telegram-фронтенд
├── web_frontend/           # Веб-фронтенд (порт 8800)
├── android/                # Android-приложение (Kotlin)
├── common/                 # Общие модули
│   ├── version.py          # Единая версия всего проекта
│   └── help_text.py        # Текст справки (используется всеми платформами)
└── docs/                   # Документация
```

---

## Версионирование

Единая версия для всех компонентов: `common/version.py`.  
Android: `versionCode = major*10000 + minor*100 + patch` (напр. 3.0.9 → 30009).  
При **любом изменении** кода любого компонента — инкрементировать patch и обновить оба файла.

---

## Тестирование

```bash
# BLS тесты
cd business_logic_service && python -m pytest tests/ -v

# Telegram Bot тесты
cd telegram_bot && python -m pytest tests/ -v

# Web тесты
cd web_frontend && python -m pytest tests/ -v
```

---

## Документация

- [Архитектура](docs/architecture.md)
- [Команды бота](docs/functionality/bot_commands.md)
- [Руководство по запуску](docs/running/running_guide.md)
- [Установка](docs/installation/installation_guide.md)

---

**Автор:** Anton Mikhalev — [@Anton_Mikhalev](https://t.me/Anton_Mikhalev)

# Language Learning Bot

Система для изучения иностранных слов с интервальным повторением.  
Версия: **3.0.26** — единая для всех компонентов (`common/version.py`).

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
- `pip install "qrcode[pil]"` (для QR-кодов в BLS)

### Запуск сервисов

```bash
sudo systemctl start langbot-backend   # порт 8500
sudo systemctl start langbot-bls       # порт 8700
sudo systemctl start langbot-web       # порт 8800
sudo systemctl start langbot-telegram  # Telegram-бот
```

Сервисы автоматически перезапускаются при изменении `.py`/`.html` файлов в `app/` и `common/`.

### Переменные окружения (`.env`)

```env
MONGODB_URL=mongodb://localhost:27027
MONGODB_DB_NAME=language_learning_bot
BACKEND_URL=http://localhost:8500
BLS_URL=http://localhost:8700
BLS_PUBLIC_URL=http://<external-ip>:8700
WEB_URL=http://<external-ip>:8800
BOT_TOKEN=...
SECRET_KEY=...
TELEGRAM_BOT_URL=https://t.me/...
```

### Сборка Android APK (release)

```bash
cd android
export ANDROID_SDK_ROOT=/home/tony/Android/Sdk
./gradlew assembleRelease
cp app/build/outputs/apk/release/app-release.apk LangBot.apk
```

Требует `android/keystore.properties` с ключом подписи (не в git).

---

## Команды Telegram-бота

| Команда | Описание |
|---------|----------|
| `/start` | Главное меню, выбор языка |
| `/study` | Продолжить текущую сессию |
| `/restart` | Начать заново (сброс сессии) |
| `/language` | Сменить язык |
| `/settings` | Настройки процесса обучения |
| `/stats` | Статистика + графики |
| `/web` | Веб-версия — код + QR для входа |
| `/android` | Скачать APK + QR-код ссылки |
| `/connect_android` | Код для входа в Android-приложение |
| `/help` | Справка |

---

## Авторизация

Все фронтенды используют единую систему одноразовых кодов:

1. **Telegram `/web`** → генерирует код, ссылка вида `http://web/login?code=XXXXXX` + QR
2. **Telegram `/connect_android`** → генерирует код для ввода в Android
3. **Веб «Код для входа»** → генерирует код для подключения другого устройства
4. **Android «Код для веб»** → генерирует код + QR для входа в браузере

Коды одноразовые, действуют 10 минут. Защита от брутфорса: блокировка после 3 неверных попыток на 1 минуту.

---

## Структура проекта

```
language-learning-bot/
├── backend/                # REST API + MongoDB (порт 8500)
├── business_logic_service/ # BLS — логика и сессии (порт 8700)
│   └── app/routers/info.py # GET /help, GET /version, GET /qr
├── telegram_bot/           # Telegram-фронтенд
├── web_frontend/           # Веб-фронтенд (порт 8800)
├── android/                # Android-приложение (Kotlin)
│   └── langbot.jks         # Ключ подписи release APK (не в git)
├── common/                 # Общие модули
│   ├── version.py          # Единая версия всего проекта
│   └── help_text.py        # Текст справки
└── docs/                   # Документация
```

---

## Версионирование

Единая версия для всех компонентов: `common/version.py`.  
Android: `versionCode = major*10000 + minor*100 + patch` (напр. 3.0.26 → 30026).  
При **любом изменении** кода — инкрементировать patch в обоих файлах.

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

---

**Автор:** Anton Mikhalev — [@Anton_Mikhalev](https://t.me/Anton_Mikhalev)

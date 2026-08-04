# Language Learning Bot

Система для изучения иностранных слов с интервальным повторением.  
Версия — единая для всех компонентов, источник правды: `common/version.py`.

Сервер: **i-04**, публичный IP `77.81.226.56`.

---

## Платформы

| Платформа | Технологии | Адрес / запуск |
|-----------|-----------|----------------|
| **Telegram-бот** | Python + aiogram 3.x | [@language_learning_words_bot](https://t.me/language_learning_words_bot) |
| **Веб-приложение** | FastAPI + Jinja2 + HTMX | порт 8548, TLS — 8444 |
| **Android** | Kotlin + Retrofit | `android/LangBot.apk` |
| **BLS** | FastAPI (логика) | порт 8531, TLS — 8443 |
| **Backend** | FastAPI + MongoDB | порт 8573 (только локально) |

Все фронтенды stateless — вся логика и состояние сессий в BLS.

### Порты наружу

| Порт | Что | Примечание |
|------|-----|------------|
| 8443 | BLS через TLS | nginx, дефолт в Android-приложении |
| 8444 | web через TLS | nginx |
| 8531 | BLS, plain HTTP | для клиентов, установленных до перехода на TLS |
| 8548 | web, plain HTTP | то же |

TLS терминирует nginx сертификатом Let's Encrypt, выписанным **на IP** —
домен не нужен. Сертификат живёт 6 дней, продлевает его x-ui; `nginx-cert-reload.path`
следит за файлом и перезагружает nginx после продления.

Порт 443 занят посторонним сервисом (xray) и проектом не используется.
Порт 80 держать свободным — там ACME-челлендж.

---

## Архитектура

```
Telegram Bot ──┐
Web Frontend   ├──► BLS (порт 8531) ──► Backend (порт 8573) ──► MongoDB
Android App  ──┘      (сессии, карточки,                       (порт 8527)
                        статистика, подсказки)
```

Подробнее: [`docs/architecture.md`](docs/architecture.md)

---

## Быстрый старт

### Требования
- Python 3.10+ (conda env `amikhalev_language_learning_bot`)
- MongoDB 7.0 (на i-04 — пользовательская установка в `~/mongodb`, порт 8527)
- Для сборки APK: **JDK 17** (AGP 8.2 / Gradle 8.4), Android SDK 34 + build-tools 34.0.0
- `pip install "qrcode[pil]"` (для QR-кодов в BLS)

### Запуск сервисов

```bash
sudo systemctl start langbot-backend   # порт 8573
sudo systemctl start langbot-bls       # порт 8531
sudo systemctl start langbot-web       # порт 8548
sudo systemctl start langbot-telegram  # Telegram-бот
```

Сервисы автоматически перезапускаются при изменении `.py`/`.html` файлов в `app/` и `common/`.

### Переменные окружения (`.env`)

```env
MONGODB_URL=mongodb://localhost:8527
MONGODB_DB_NAME=language_learning_bot
BACKEND_URL=http://localhost:8573
BLS_URL=http://localhost:8531
BLS_PUBLIC_URL=http://<external-ip>:8531
WEB_URL=http://<external-ip>:8548
BOT_TOKEN=...
SECRET_KEY=...
TELEGRAM_BOT_URL=https://t.me/...
```

### Сборка Android APK

```bash
cd android
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export ANDROID_SDK_ROOT=$HOME/Android/Sdk
./gradlew testDebugUnitTest   # JVM-тесты (Robolectric + MockWebServer, эмулятор не нужен)
./gradlew assembleRelease     # требует langbot.jks + keystore.properties
cp app/build/outputs/apk/release/app-release.apk LangBot.apk
```

> ⚠️ **Раздавать можно только release-сборку.** Debug подписан ключом
> `CN=Android Debug` и **не встанет поверх** установленного приложения —
> Android откажет с `INSTALL_FAILED_UPDATE_INCOMPATIBLE`.
>
> Отпечаток боевого ключа (должен совпадать у каждой сборки):
> `0b21ffd8a4c13883dc78727e23b79384122ff1d1eccb87a23a0285ba3a931d31`
>
> Проверка: `apksigner verify --print-certs android/LangBot.apk`
>
> Потеря `langbot.jks` необратима: всем придётся удалять и ставить приложение
> заново, теряя сохранённый вход. Держите копию **вне сервера**.

Подробнее: [docs/development/android_build.md](docs/development/android_build.md)

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
| `/admin` | Панель администратора — **только для админов** |

`/admin` намеренно нет в общем списке команд: он публичный, и команду увидели бы все.
Администраторам она добавляется персонально через `BotCommandScopeChat` при каждом
`/start`, там же в меню появляется кнопка «⚙️ Админка». Снятие прав убирает и то, и
другое при следующем `/start`.

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
├── backend/                # REST API + MongoDB (порт 8573)
├── business_logic_service/ # BLS — логика и сессии (порт 8531)
│   └── app/routers/info.py # GET /help, GET /version, GET /qr
├── telegram_bot/           # Telegram-фронтенд
├── web_frontend/           # Веб-фронтенд (порт 8548)
├── android/                # Android-приложение (Kotlin)
│   ├── langbot.jks         # Ключ подписи release APK (не в git!)
│   └── keystore.properties # Пароли к ключу (не в git!)
├── frontend/               # ЛЕГАСИ: старый Telegram-бот, заменён telegram_bot/,
│                           # не запускается, юнита нет
├── common/                 # Общие модули
│   ├── version.py          # Единая версия всего проекта
│   └── help_text.py        # Текст справки
└── docs/                   # Документация
```

---

## Версионирование

Единая версия для всех компонентов: `common/version.py`.
Android `versionCode` вычисляется из неё автоматически:
`major*10000 + minor*100 + patch` (напр. 3.0.72 → 30072) — править `build.gradle` не нужно.

> ⛔ **Версию нельзя двигать отдельно от пересборки APK.**
>
> `LanguagesActivity` сравнивает `version_code` из BLS `/version` с установленным.
> Подняли версию, не пересобрав `android/LangBot.apk` — у **всех** пользователей
> появится баннер обновления, ведущий на сборку, которой не существует.
>
> Правило: бамп версии → тесты → `./gradlew assembleRelease` тем же keystore →
> `cp app/build/outputs/apk/release/app-release.apk android/LangBot.apk` → коммит.
> Всё одним изменением.

Имя файла на `/download/android` читается **из самого APK**, а не из `version.py`,
поэтому рассинхрон имени и содержимого невозможен.

---

## Тестирование

```bash
# Всё сразу — bls, telegram, web, backend, common, legacy frontend
python run_tests.sh

# Отдельный компонент
python run_tests.sh -c bls

# Android (JVM, эмулятор не нужен)
cd android && ./gradlew testDebugUnitTest
```

`run_tests.sh` трактует код выхода pytest 5 («ничего не собрано, всё заскипано»)
как успех — тесты, заскипанные на уровне модуля, объясняют причину прямо в файле.

---

## Документация

- [Архитектура](docs/architecture.md)
- [Команды бота](docs/functionality/bot_commands.md)
- [Офлайн-кеширование на Android](docs/development/offline_caching.md)
- [Сборка APK](docs/development/android_build.md)

---

**Автор:** Anton Mikhalev — [@Anton_Mikhalev](https://t.me/Anton_Mikhalev)

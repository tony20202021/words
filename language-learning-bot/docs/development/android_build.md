# Сборка Android APK

## Требования

- **JDK 17** — в окружении доступен через conda (`/home/tony/miniconda3/bin/java`)
- **Android SDK** — путь: `/home/tony/Android/Sdk`
- Gradle wrapper (`./gradlew`) — скачивает зависимости сам, отдельная установка не нужна

## JAVA_HOME

JDK 17 поставляется с conda и настраивается автоматически при активном окружении.
Если `./gradlew` падает с ошибкой «No Java found» или «JAVA_HOME is not set»:

```bash
export JAVA_HOME=/home/tony/miniconda3
export ANDROID_SDK_ROOT=/home/tony/Android/Sdk
```

Можно добавить в `~/.zshrc` постоянно, но при активном conda-окружении обычно уже работает.

## Debug vs Release

| | Debug | Release |
|---|---|---|
| Команда | `./gradlew assembleDebug` | `./gradlew assembleRelease` |
| Выходной файл | `app/build/outputs/apk/debug/app-debug.apk` | `app/build/outputs/apk/release/app-release.apk` |
| Подпись | Авто (debug-ключ Android SDK) | Keystore из `keystore.properties` |
| Для раздачи | Можно, если только для тестирования | Да — production APK |

**Debug** — быстро, не нужен keystore, подходит для разработки и тестирования.  
**Release** — требует `android/keystore.properties` (не в git), production-сборка.

## Процедура сборки

### 1. Обновить версию

Версия читается автоматически из `common/version.py` — `build.gradle` вызывает Python при каждой сборке:

```python
# common/version.py
__version__ = "3.0.47"
```

`versionCode` считается автоматически: `major*10000 + minor*100 + patch` (например, 3.0.47 → 30047).

### 2. Собрать

```bash
cd /home/tony/repos/words/language-learning-bot/android

# Debug (рекомендуется для разработки):
export ANDROID_SDK_ROOT=/home/tony/Android/Sdk
./gradlew assembleDebug

# Release (production):
export ANDROID_SDK_ROOT=/home/tony/Android/Sdk
./gradlew assembleRelease
```

### 3. Скопировать APK для раздачи

```bash
# Debug:
cp app/build/outputs/apk/debug/app-debug.apk LangBot.apk

# Release:
cp app/build/outputs/apk/release/app-release.apk LangBot.apk
```

Файл `android/LangBot.apk` отдаётся ботом по команде `/android`.

## Keystore для Release

Файл `android/keystore.properties` (не в git):

```properties
storeFile=../langbot.jks
storePassword=...
keyAlias=langbot
keyPassword=...
```

Сам ключ: `android/langbot.jks` (тоже не в git).  
Если файл отсутствует — `build.gradle` молча использует пустые значения, сборка упадёт при подписи.

## Проверка версии внутри APK

**Всегда проверять версию внутри собранного APK** — особенно если Gradle кэшировал старый результат:

```bash
# Через aapt:
aapt dump badging android/LangBot.apk | grep versionName

# Или через gradlew:
cd android && ./gradlew -q printVersionName
```

Ожидаемый вывод: `versionName='3.0.47'` — должен совпадать с `common/version.py`.

## Если версия внутри APK старая

`build.gradle` иногда кэширует результат Python-вызова. Помогает чистая сборка:

```bash
./gradlew clean assembleDebug
```

## Что требует пересборки APK

| Изменение | Нужна пересборка? |
|---|---|
| `common/version.py` | Да |
| `android/app/src/main/**` (Kotlin, XML) | Да |
| BLS / backend API (изменился контракт) | Да |
| Только Python-сервисы (BLS, web, telegram) | Нет |

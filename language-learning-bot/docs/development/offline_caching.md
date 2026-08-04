# Офлайн-кеширование на Android (дизайн)

Статус: **Все три фазы реализованы** (Ф1+Ф2 — v3.0.67, Ф3 кеш аудио + дедуп — v3.0.68).
См. раздел «Реализация» внизу.

Проблема: сейчас при отсутствии сети приложение просто «висит» с ошибкой на
одном экране — учебный цикл полностью управляется сервером (каждое действие
делает HTTP-round-trip к BLS и получает готовую карточку). Web-клиент и
Telegram-бот тоже серверные, но для них клиентское хранилище нецелесообразно;
фокус — **Android**.

## Аудит: точки обмена Android ↔ BLS

Источник: `android/app/src/main/java/com/langbot/app/network/BLSService.kt`.
Локального хранилища на Android нет (ни Room, ни DataStore, ни SharedPreferences).

| Категория | Вызовы | Стратегия офлайн |
|-----------|--------|------------------|
| Учебный цикл (мутируют состояние, возвращают следующую карточку) | `startSession`, `showAnswer`, `rateWord`, `knowWord`, `pickAnswer`, `reconsider`, `toggleSkip`, `nextBatch` | локальный движок из кеша + outbox |
| Отправка результата | `rateWord`, `knowWord`, `pickAnswer` | **outbox** (очередь неотправленных) |
| Прочие записи | `setHint`, `deleteHint`, `toggleSetting`, `setSetting`, `addForbiddenPair`, `clearForbiddenPairs`, `endSession` | общая очередь записей |
| Чтение | `getLanguages`, `getSettings`, `getStatistics`, `getHints` | кешировать last-known, показывать stale |
| Только онлайн | auth (`activateMobileToken`/`createMobileToken`), `getChart*`, `getQrCode`, `getVersion`, `getHelp` | оставить как есть |

Карточка (`Card` в `network/ApiModels.kt`) полностью рендерится сервером:
`content[]`, `buttons[]`, `meta`, `sounds[]`, `pick_options`.

## Архитектура решения

### 1. Префетч-бандл при старте сессии (BLS → Android)
Новый эндпоинт `POST /session/{user_id}/{language_id}/bundle` возвращает не одну
карточку, а пачку N≈100 «юнитов слова», каждый готов для всех экранов:

```
{ session_id,
  words: [ {
     word_id, word_number,
     card_front,             // отрендеренная card_builder'ом «вопросная» сторона
     card_answer,            // отрендеренная «ответная» сторона
     sounds: [paths...],
     hints: {...},
     pick_options: {...}     // если pick mode — заранее сгенерённый КОНКРЕТНЫЙ набор дистракторов
  }, ... ],
  settings, progress_snapshot }
```
Клиент становится чистым рендерером кеша → минимум клиентской логики,
переиспользуются серверные `card_builder` и `quiz_service`.

### 2. Локальный движок сессии (Android)
`SessionCache` (Room или JSON в `filesDir`) хранит бандл + курсор. Действия
работают по кешу: `show_answer` → показать `card_answer`; `rate/know/pick` →
записать результат в outbox и сдвинуть курсор. Курсор дошёл до конца бандла →
запросить следующий (онлайн) либо показать «партия пройдена, подключитесь».

### 3. Outbox — очередь неотправленных результатов
Персистентная очередь событий `{event_id (uuid), word_id, rating, ts}`. На
каждый рейтинг: применить локально (сдвиг) + положить в очередь. Флаш при:
возврате сети / фокусе приложения / перед запросом нового бандла →
`POST /results/batch { user_id, language_id, events:[...] }`. BLS применяет
каждый результат тем же алгоритмом интервального повторения, **идемпотентно по
event_id**, в порядке `ts`.

### 4. Новый BLS-эндпоинт `POST /results/batch`
Применяет список результатов напрямую по `word_id` (не привязан к in-memory
сессии), переиспользуя текущую логику начисления балла/интервала
(`backend` update_score / spaced-repetition). Возвращает ack по каждому
`event_id`. Идемпотентность — хранить обработанные `event_id` или дедуп по
`(word_id, ts)`.

### 5. UX связи
Вместо застревания — баннер «Офлайн — занимайтесь, результаты уйдут позже
(N в очереди)». `ConnectivityManager` ловит возврат сети → автофлаш. Никаких
блокирующих ошибок в учебном цикле.

### 6. Персистентность
Room (рекомендуется). Таблицы: `cached_bundle` (юниты слова + курсор),
`outbox` (события результатов и прочих записей).

## План изменений по фазам

**Фаза 1 — Outbox (быстро, максимум пользы).** ✅ Реализовано. Очередь для
`rate/know/pick`, флаш при сбое/реконнекте. Устраняет «висит с ошибкой».
- Android: файловый `OfflineCache` (Gson + `filesDir`, без Room) + `OutboxSync` +
  `ConnectivityManager.registerDefaultNetworkCallback` в `LangBotApp` (без WorkManager).
- BLS: эндпоинт `POST /results/batch` (идемпотентность по `event_id`, порядок по `ts`).

**Фаза 2 — Префетч-бандл + локальный движок.** ✅ Реализовано. Истинный офлайн-цикл.
- BLS: `POST /session/{u}/{l}/bundle` (`start_session(register=False)` — снапшот, не
  трогает активную сессию; рендер обеих карточек + pick_options наперёд).
- Android: `OfflineEngine` + фолбэк в `StudyActivity` (при сетевой ошибке действие
  применяется к кешу, следующая карточка — из бандла).

**Фаза 3 — Кеш аудио.** ✅ Реализовано (v3.0.68). `AudioCache` докачивает mp3 всех
слов бандла в `filesDir/sounds/` (фоново, при префетче); `playSoundSequence` берёт
локальный файл, если он есть, иначе стримит из BLS. → звук работает офлайн.

## Дедупликация бизнес-логики (v3.0.68)

Проблема: офлайн-движок Android частично повторял логику BLS (какая кнопка что
делает, какой рейтинг записать). Решение — **BLS остаётся единственным источником
правды**, а Android становится «тупым плеером»: `build_card` штампует на каждую
кнопку `offline_effect` (`reveal_answer` | `reveal_question` | `submit`) и
`offline_rating`, а на каждый pick-вариант — `offline_rating` (`know`/`dont_know`
по `is_correct`). Офлайн Android читает эти метки **из кешированного бандла** (не из
сети!) и просто исполняет — своих правил не имеет.

Важно: «тупой плеер» полностью автономен офлайн — вся семантика предвычислена BLS
онлайн и лежит в бандле на устройстве. `OfflineSemantics` (Android) — лишь compat-
fallback по id кнопки для бандлов, закешированных до появления этих полей.

## Реализация (v3.0.67–3.0.68)

Модель работы — **онлайн-первично + офлайн-фолбэк + всегда-включённый outbox**:
онлайн-путь не изменён (нулевая регрессия); при сетевой ошибке во время действия
результат кладётся в outbox, а следующая карточка берётся из кешированного бандла
(режим офлайн); `ConnectivityManager` флашит outbox при возврате сети; бандл
префетчится в фоне при старте сессии.

Ключевые файлы:
- BLS: `services/session_service.py` (`build_bundle`, `apply_results_batch`,
  `start_session(register=...)`), `services/card_builder.py` (`offline_effect`/
  `offline_rating` на кнопках и pick-вариантах), `routers/session.py` (`/bundle`),
  `routers/results.py`.
- Android: `network/ApiModels.kt` (`BundleResponse`/`ResultsBatchRequest`, поля
  `offline_effect`/`offline_rating`), `network/BLSService.kt` (`getBundle`/
  `postResultsBatch`), `offline/Offline.kt` (`OfflineCache`/`OutboxSync`/
  `OfflineEngine`), `offline/AudioCache.kt` (кеш mp3), `offline/OfflineSemantics.kt`
  (compat-fallback), `LangBotApp.kt` (init + авто-флаш), `StudyActivity.kt`
  (префетч бандла+аудио, офлайн-фолбэк, «тупой плеер»).

Офлайн-исполнение действий (метки из бандла): `offline_effect=reveal_answer`→
показать ответ; `reveal_question`→вернуть вопрос; `submit`→записать `offline_rating`
в outbox + перейти к следующему. Pick-ответ → записать `offline_rating` варианта.
`add_forbidden_pair` офлайн недоступен.

Тесты: BLS — `tests/test_offline_bundle.py`, `tests/test_card_builder.py`
(офлайн-семантика кнопок/опций), `tests/test_integration/test_bls_api.py`
(`TestOfflineEndpoints`). Android — `app/src/test/.../OfflineLogicTest.kt`
(чистая логика: `AudioCache.fileNameFor`, `OfflineSemantics`, `OfflineCache.tsOf`),
запуск `./gradlew testReleaseUnitTest` (без эмулятора).

## Риски / нюансы
- Реиграние рейтингов чувствительно к порядку (интервал зависит от прошлого
  балла) → строго по `ts` + идемпотентность по `event_id`.
- Размер бандла (100 слов × 2 карточки × pick_options) — терпимо (текст).
- Аудио офлайн: mp3 кешируются в `filesDir/sounds/` при префетче (Ф3, реализовано).
- Web/Telegram: офлайн-цикл нецелесообразен; максимум — дружелюбная страница ошибки.

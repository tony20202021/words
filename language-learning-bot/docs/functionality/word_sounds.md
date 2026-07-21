# Озвучка слов (word sounds)

Документ описывает, как в проекте устроена озвучка слов: хранение, отдача,
формат данных и генерация аудио для нового языка (на примере китайского и иврита).

## Хранение и отдача

- Файлы `.mp3` лежат в каталоге `backend/data/sounds/…`.
  Базовый путь задаётся в [`backend/conf/config/sounds.yaml`](../../backend/conf/config/sounds.yaml) → `sound_path`.
- Бэкенд отдаёт файлы по эндпоинту `GET /api/sounds/{путь}`
  (см. `backend/app/api/routes/sounds.py`, `backend/app/services/sound_service.py`),
  `Content-Type: audio/mpeg`.
- Пример: файл `backend/data/sounds/he/gtts/232.mp3` доступен по
  `GET /api/sounds/sounds/he/gtts/232.mp3`.

## Поле `sounds` у слова

У документа слова в коллекции `words` есть строковое поле `sounds` — JSON с картой
«ключ голоса → относительный путь к mp3»:

```json
{"sound_1": "sounds/he/gtts/232.mp3", "sound_2": "sounds/he/hila/232.mp3", "sound_3": "sounds/he/avri/232.mp3"}
```

Его читает `business_logic_service/app/services/card_builder.py`
(`_parse_sound_urls`): значения сортируются по ключу и отдаются в карточку.
Показ звука управляется настройкой пользователя `show_sounds`.

Никаких изменений в коде бота для нового языка не требуется — достаточно положить
mp3-файлы и заполнить поле `sounds`.

## Генерация: китайский

Скрипт [`words/words/sounds/sounds_all.py`](../../../words/sounds/sounds_all.py), три источника:

- `sound_1` / `sound_2` — mp3 отдельных иероглифов (скачаны с Yoyo Chinese и
  ArchChinese), склеиваются в слово через `pydub`.
- `sound_3` — Google TTS (`gTTS`, `lang='zh-CN'`) целым словом.

## Генерация: иврит

У иврита нет посимвольных звуков, поэтому озвучиваются слова целиком **тремя
разными голосами** (аналог `sound_1/2/3`):

| Ключ | Голос | Источник |
|------|-------|----------|
| `sound_1` | Google | `gTTS`, `lang='iw'` (код `he` не поддерживается) |
| `sound_2` | Hila (женский, нейронный) | `edge-tts`, `he-IL-HilaNeural` |
| `sound_3` | Avri (мужской, нейронный) | `edge-tts`, `he-IL-AvriNeural` |

Файлы: `backend/data/sounds/he/{gtts,hila,avri}/<word_number>.mp3`.
Скрипт-пример: `words/words/data/hebrew_freq/gen_sounds_1000.py`.

### Обрезка тишины (обязательно)

Нейронные голоса `edge-tts` дают в конце паузу до ~1.2 с (и в начале ~0.3 с) —
при проигрывании нескольких голосов подряд получается длинный провал. После
генерации каждый файл прогоняется через обрезку тишины:

- `pydub.silence.detect_leading_silence`, порог `-40 dB`, оставляем ~40 мс отступа
  с каждого края, экспорт `mp3` `bitrate=48k`.

Зависимости для генерации: `gtts`, `edge-tts`, `pydub` (+ `ffmpeg`).
Установка `gtts` понижает `click` до 8.1.8; сервисы бота `typer` не используют,
но полный прогон 10 000 слов лучше делать в изолированном venv.

## Проверка

```
curl -s -o /tmp/x.mp3 http://localhost:8573/api/sounds/sounds/he/hila/4.mp3
```

Ожидается `200`, валидный MP3 (сигнатура `ID3`/`FF Fx`).

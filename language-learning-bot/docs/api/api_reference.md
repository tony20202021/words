# API клиент

## Содержание
1. [Обзор](#обзор)
2. [Инициализация](#инициализация)
3. [Формат ответов](#формат-ответов)
4. [Методы для работы с языками](#методы-для-работы-с-языками)
5. [Методы для работы со словами](#методы-для-работы-со-словами)
6. [Методы для работы с пользователями](#методы-для-работы-с-пользователями)
7. [Методы для работы с данными слов пользователя](#методы-для-работы-с-данными-слов-пользователя)
8. [Методы для получения прогресса](#методы-для-получения-прогресса)
9. [Методы для получения слов для изучения](#методы-для-получения-слов-для-изучения)
10. [Методы для работы с настройками](#методы-для-работы-с-настройками)
11. [Обработка ошибок](#обработка-ошибок)
12. [Примечания](#примечания)
13. [Обновления во фронтенде](#обновления-во-фронтенде)

## Обзор

API клиент предоставляет удобный интерфейс для взаимодействия фронтенда (Telegram-бота) с бэкендом (REST API). Он инкапсулирует логику HTTP-запросов, обработку ошибок и повторные попытки.

## Инициализация

```python
from app.api.client import APIClient

# Инициализация с параметрами по умолчанию
api_client = APIClient()

# Инициализация с пользовательскими параметрами
api_client = APIClient(
    base_url="http://custom-backend.com",
    timeout=10
)
```

## Формат ответов

Все методы API клиента возвращают унифицированную структуру ответа:

```python
{
    "success": bool,    # True если запрос успешен, False в случае ошибки
    "status": int,      # HTTP-статус код (200, 201, 404, 500 и т.д.) или 0 при ошибке соединения
    "result": Any,      # Данные ответа или None
    "error": str        # Сообщение об ошибке или None, если ошибки не было
}
```

Пример обработки ответа:

```python
response = await api_client.get_languages()
if response["success"]:
    languages = response["result"]
    # Обработка полученных данных
else:
    error_msg = response.get("error", "Неизвестная ошибка")
    # Обработка ошибки
```

## Методы для работы с языками

### get_languages()

Получение списка всех языков.

```python
languages_response = await api_client.get_languages()
if languages_response["success"]:
    languages = languages_response["result"]
    for language in languages:
        print(f"ID: {language['id']}, Название: {language['name_ru']}")
```

### get_language(language_id)

Получение информации о конкретном языке по ID.

```python
language_response = await api_client.get_language("123abc")
if language_response["success"]:
    language = language_response["result"]
    print(f"Название: {language['name_ru']}, Оригинал: {language['name_foreign']}")
```

### create_language(language_data)

Создание нового языка.

```python
language_data = {
    "name_ru": "Французский",
    "name_foreign": "Français"
}
result = await api_client.create_language(language_data)
if result["success"]:
    created_language = result["result"]
    print(f"Создан язык с ID: {created_language['id']}")
```

### update_language(language_id, language_data)

Обновление существующего языка.

```python
update_data = {
    "name_ru": "Французский (обновлено)"
}
result = await api_client.update_language("123abc", update_data)
if result["success"]:
    updated_language = result["result"]
    print(f"Обновлен язык: {updated_language['name_ru']}")
```

### delete_language(language_id)

Удаление языка по ID.

```python
result = await api_client.delete_language("123abc")
if result["success"]:
    print("Язык успешно удален")
```

### get_word_count_by_language(language_id)

Получение количества слов для языка.

```python
result = await api_client.get_word_count_by_language("123abc")
if result["success"]:
    word_count = result["result"]["count"]
    print(f"Количество слов в языке: {word_count}")
```

## Методы для работы со словами

### get_words_by_language(language_id, skip, limit)

Получение списка слов для конкретного языка с пагинацией.

```python
words_response = await api_client.get_words_by_language("123abc", skip=0, limit=100)
if words_response["success"]:
    words = words_response["result"]
    for word in words:
        print(f"Слово: {word['word_foreign']}, Перевод: {word['translation']}")
```

### get_word(word_id)

Получение информации о конкретном слове по ID.

```python
word_response = await api_client.get_word("word123")
if word_response["success"]:
    word = word_response["result"]
    print(f"Слово: {word['word_foreign']}, Перевод: {word['translation']}")
```

### get_word_by_number(language_id, word_number)

Получение слова по номеру и ID языка.

```python
word_response = await api_client.get_word_by_number("123abc", 1)
if word_response["success"]:
    # Обработка результата, который может быть словарем или списком
    words = word_response["result"]
    word = words[0] if isinstance(words, list) and len(words) > 0 else words
    
    if word:
        print(f"Слово №{word['word_number']}: {word['word_foreign']}")
        print(f"Транскрипция: {word.get('transcription')}")
        print(f"Перевод: {word.get('translation')}")
    else:
        print(f"Слово с номером 1 не найдено")
else:
    error_msg = word_response.get("error", "Неизвестная ошибка")
    print(f"Ошибка при поиске слова: {error_msg}")
```

**Примечание:** Этот метод особенно полезен для администраторов, которые хотят быстро найти и проверить слово в частотном списке. В административной панели бота реализован удобный интерфейс для поиска слова по номеру с отображением всей информации о найденном слове.

### create_word(word_data)

Создание нового слова.

```python
word_data = {
    "language_id": "123abc",
    "word_foreign": "bonjour",
    "translation": "здравствуйте",
    "transcription": "bɔ̃ʒuʁ",
    "word_number": 1
}
result = await api_client.create_word(word_data)
if result["success"]:
    created_word = result["result"]
    print(f"Создано слово с ID: {created_word['id']}")
```

### update_word(word_id, word_data)

Обновление существующего слова.

```python
update_data = {
    "translation": "привет",
    "transcription": "bɔ̃ʒuʁ (обновлено)"
}
result = await api_client.update_word("word123", update_data)
if result["success"]:
    updated_word = result["result"]
    print(f"Обновлено слово: {updated_word['word_foreign']}")
```

### delete_word(word_id)

Удаление слова по ID.

```python
result = await api_client.delete_word("word123")
if result["success"]:
    print("Слово успешно удалено")
```

### upload_words_file(language_id, file_data, file_name, params, timeout_multiplier)

Загрузка файла со словами для конкретного языка.

**Параметры:**
- `language_id` (str): ID языка
- `file_data` (bytes): Бинарное содержимое файла
- `file_name` (str): Имя файла
- `params` (dict, опционально): Параметры для обработки файла
  - `column_word` (int): Индекс колонки для иностранных слов
  - `column_translation` (int): Индекс колонки для переводов
  - `column_transcription` (int): Индекс колонки для транскрипций
  - `column_number` (int, опционально): Индекс колонки для номеров слов
  - `start_row` (int): Индекс строки для начала обработки (1-based)
- `timeout_multiplier` (int, опционально): Множитель для таймаута запроса (по умолчанию: 3). Операции с файлами обычно занимают больше времени, чем обычные API-запросы.

**Возвращает:**
- Словарь с результатами загрузки согласно стандартной структуре ответа

```python
# Загрузка файла из Telegram
file_data = await bot.download_file_by_id(file_id)
result = await api_client.upload_words_file(
    language_id="123abc", 
    file_data=file_data, 
    file_name="words.xlsx",
    params={
        "column_word": 0,
        "column_translation": 1,
        "column_transcription": 2,
        "start_row": 1
    },
    timeout_multiplier=5  # Увеличенный таймаут для большого файла
)
if result["success"]:
    upload_stats = result["result"]
    print(f"Обработано слов: {upload_stats['total_words_processed']}")
    print(f"Добавлено: {upload_stats['words_added']}")
    print(f"Обновлено: {upload_stats['words_updated']}")
```

## Методы для работы с пользователями

### get_user_by_telegram_id(telegram_id)

Получение информации о пользователе по Telegram ID.

```python
user_response = await api_client.get_user_by_telegram_id(123456789)
if user_response["success"]:
    users = user_response["result"]
    user = users[0] if users and len(users) > 0 else None
    
    if user:
        print(f"Пользователь найден: {user['first_name']} {user['last_name']}")
    else:
        print("Пользователь не найден, необходимо создать")
```

### create_user(user_data)

Создание нового пользователя.

```python
user_data = {
    "telegram_id": 123456789,
    "username": "john_doe",
    "first_name": "John",
    "last_name": "Doe"
}
result = await api_client.create_user(user_data)
if result["success"]:
    created_user = result["result"]
    print(f"Создан пользователь с ID: {created_user['id']}")
```

### update_user(user_id, user_data)

Обновление существующего пользователя.

```python
update_data = {
    "is_admin": True
}
result = await api_client.update_user("user123", update_data)
if result["success"]:
    updated_user = result["result"]
    print(f"Пользователь обновлен, статус администратора: {updated_user['is_admin']}")
```

## Методы для работы с данными слов пользователя

### get_user_word_data(user_id, word_id)

Получение данных пользователя для конкретного слова.

```python
word_data_response = await api_client.get_user_word_data("user123", "word123")
if word_data_response["success"]:
    word_data = word_data_response["result"]
    
    if word_data:
        print(f"Оценка: {word_data.get('score')}")
        print(f"Интервал: {word_data.get('check_interval')} дней")
        print(f"Следующая проверка: {word_data.get('next_check_date')}")
        
        # Подсказки
        print(f"Фонетика: {word_data.get('hint_syllables')}")
        print(f"Ассоциация: {word_data.get('hint_association')}")
        print(f"Значение: {word_data.get('hint_meaning')}")
        print(f"Написание: {word_data.get('hint_writing')}")
    else:
        print("Данные для слова отсутствуют")
```

### create_user_word_data(user_id, word_data)

Создание данных слова для пользователя.

```python
word_data = {
    "word_id": "word123",
    "language_id": "123abc",
    "hint_association": "моя подсказка",
    "score": 0,
    "is_skipped": False
}
result = await api_client.create_user_word_data("user123", word_data)
if result["success"]:
    created_data = result["result"]
    print(f"Созданы данные слова для пользователя")
```

### update_user_word_data(user_id, word_id, word_data)

Обновление данных слова для пользователя.

```python
update_data = {
    "score": 1,
    "check_interval": 2,
    "hint_association": "новая подсказка"
}
result = await api_client.update_user_word_data("user123", "word123", update_data)
if result["success"]:
    updated_data = result["result"]
    print(f"Данные слова обновлены, новый интервал: {updated_data['check_interval']} дней")
```

## Методы для получения прогресса

### get_user_progress(user_id, language_id)

Получение прогресса пользователя для конкретного языка.

```python
progress_response = await api_client.get_user_progress("user123", "123abc")
if progress_response["success"]:
    progress = progress_response["result"]
    
    print(f"Язык: {progress['language_name_ru']}")
    print(f"Всего слов: {progress['total_words']}")
    print(f"Изучено слов: {progress['words_studied']}")
    print(f"Известно слов: {progress['words_known']}")
    print(f"Прогресс: {progress['progress_percentage']}%")
```

## Методы для получения слов для изучения

### get_study_words(user_id, language_id, params, limit)

Получение слов для изучения с учетом всех фильтров.

**Параметры:**
- `user_id` (str): ID пользователя
- `language_id` (str): ID языка
- `params` (dict): Параметры для фильтрации слов
  - `start_word` (int): Номер слова, с которого начать (по умолчанию: 1)
  - `skip_marked` (bool): Пропускать помеченные слова (по умолчанию: False)
  - `use_check_date` (bool): Учитывать дату следующей проверки (по умолчанию: True)
- `limit` (int, опционально): Максимальное количество возвращаемых слов (по умолчанию: 100)

**Возвращает:**
- Словарь с результатами согласно стандартной структуре ответа
- В случае успеха, `result` содержит список слов для изучения с учетом указанных фильтров

```python
params = {
    "start_word": 1,            # Начинать с этого номера слова
    "skip_marked": True,        # Пропускать помеченные слова
    "use_check_date": True      # Учитывать дату следующей проверки
}

words_response = await api_client.get_study_words(
    user_id="user123", 
    language_id="123abc", 
    params=params,
    limit=50
)

if words_response["success"]:
    words = words_response["result"]
    
    if words and len(words) > 0:
        print(f"Получено {len(words)} слов для изучения")
        word = words[0]
        print(f"Слово для изучения: {word.get('word_foreign')}")
        print(f"Перевод: {word.get('translation')}")
        print(f"Транскрипция: {word.get('transcription')}")
        
        # Проверка наличия данных пользователя для слова
        user_word_data = word.get("user_word_data")
        if user_word_data:
            print(f"Оценка: {user_word_data.get('score')}")
            print(f"Подсказка: {user_word_data.get('hint_association')}")
    else:
        print("Нет слов для изучения с текущими настройками")
```

## Методы для работы с настройками

### get_user_language_settings(user_id, language_id)

Получение настроек пользователя для конкретного языка.

```python
settings_response = await api_client.get_user_language_settings("user123", "123abc")
if settings_response["success"]:
    settings = settings_response["result"]
    
    print(f"Начальное слово: {settings['start_word']}")
    print(f"Пропускать помеченные: {settings['skip_marked']}")
    print(f"Учитывать дату проверки: {settings['use_check_date']}")
    print(f"Показывать подсказки: {settings['show_hints']}")
```

### update_user_language_settings(user_id, language_id, settings_data)

Обновление настроек пользователя для конкретного языка.

```python
settings_data = {
    "start_word": 5,
    "skip_marked": True,
    "use_check_date": False,
    "show_hints": True
}
result = await api_client.update_user_language_settings("user123", "123abc", settings_data)
if result["success"]:
    updated_settings = result["result"]
    print(f"Настройки обновлены")
```

### get_all_user_settings(user_id)

Получение всех настроек пользователя по всем языкам.

```python
settings_response = await api_client.get_all_user_settings("user123")
if settings_response["success"]:
    all_settings = settings_response["result"]
    
    print(f"Найдено настроек для {len(all_settings)} языков")
    for settings in all_settings:
        language_id = settings['language_id']
        print(f"Настройки для языка {language_id}:")
        print(f"  Начальное слово: {settings['start_word']}")
        print(f"  Пропускать помеченные: {settings['skip_marked']}")
```

## Обработка ошибок

API клиент обеспечивает стандартизированную обработку ошибок. Рекомендуется всегда проверять ключ `"success"` и обрабатывать возможные ошибки:

```python
response = await api_client.get_languages()
if response["success"]:
    # Обработка успешного ответа
    languages = response["result"]
    # ...
else:
    # Обработка ошибки
    error_msg = response.get("error", "Неизвестная ошибка")
    status_code = response.get("status", 0)
    
    if status_code == 404:
        # Ресурс не найден
        print(f"Ресурс не найден: {error_msg}")
    elif status_code >= 500:
        # Ошибка сервера
        print(f"Ошибка сервера: {error_msg}")
    else:
        # Другие ошибки
        print(f"Ошибка: {error_msg}")
```

### Типы ошибок и их обработка

API клиент может возвращать следующие типы ошибок:

1. **Ошибки сети** (status = 0)
   - Проблемы с подключением к бэкенду
   - Таймауты запросов

2. **Ошибки клиента** (400-499)
   - 400 Bad Request - некорректные параметры запроса
   - 404 Not Found - ресурс не найден
   - 422 Unprocessable Entity - ошибка валидации данных

3. **Ошибки сервера** (500-599)
   - 500 Internal Server Error - внутренняя ошибка сервера
   - 503 Service Unavailable - сервис временно недоступен

4. **Пользовательские ошибки**
   - Специфические для API бизнес-ошибки

### Автоматические повторные попытки

API клиент автоматически повторяет запросы при некоторых типах ошибок (таймауты, временные ошибки сервера). Количество повторных попыток и задержка между ними настраиваются при инициализации клиента:

```python
api_client = APIClient(
    base_url="http://localhost:8500",
    timeout=5,
    retry_count=3,
    retry_delay=1
)
```

При исчерпании повторных попыток клиент вернет последнюю полученную ошибку.

## Примечания

1. Большинство методов API клиента возвращают результат в ключе `"result"` в виде:
   - Объекта (dict) для одиночных записей
   - Списка объектов (list[dict]) для коллекций

2. Если запрашиваемый ресурс не найден (например, пользователь по Telegram ID), результат может быть:
   - Пустым списком `[]` - для методов, которые предполагают возврат коллекции
   - `None` - для методов, которые возвращают одиночный объект

3. Методы, которые удаляют ресурсы (например, `delete_language`), обычно возвращают в ключе `"result"` сообщение об успешном удалении.

4. API клиент автоматически выполняет повторные попытки для временных ошибок (таких как ошибки сервера или проблемы с сетью).

## Обновления во фронтенде

Следующие изменения были внесены в фронтенд (Telegram-бот) для улучшения API клиента:

1. **API клиент**:
   - Добавлены и исправлены методы `get_user_language_settings` и `update_user_language_settings` в `client.py`

2. **Модульная структура**:
   - Вынесен код обработчиков пользователя в отдельные модули в каталоге `app/bot/handlers/user/`
   - Реализованы отдельные модули для настроек, подсказок, статистики и базовых команд

3. **Вспомогательные модули**:
   - Создан модуль `app/utils/settings_utils.py` с функциями для работы с настройками
   - Обновлен `app/utils/formatting_utils.py` для поддержки отображения настроек по языкам
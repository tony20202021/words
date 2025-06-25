# Документация по Backend API

## Общая информация

Backend API предоставляет RESTful интерфейс для взаимодействия с базой данных MongoDB. API используется фронтендом (Telegram-ботом) и может использоваться любыми другими клиентами.

- **Базовый URL API**: `/api`
- **Документация API**: `/api/docs` (Swagger UI)
- **Альтернативная документация**: `/api/redoc` (ReDoc)
- **OpenAPI спецификация**: `/api/openapi.json`

## Аутентификация

В текущей версии API не используется аутентификация. API предназначен для внутреннего использования ботом Telegram. В будущем может быть добавлена аутентификация на основе JWT (JSON Web Tokens).

## Общие параметры запроса

- **skip** (int, опционально) - Количество записей для пропуска (пагинация)
- **limit** (int, опционально) - Максимальное количество возвращаемых записей

## Формат ответов

API использует JSON для всех запросов и ответов. Структура ответа:

```json
{
  "success": true,          // Статус выполнения запроса
  "status": 200,            // HTTP-статус код
  "result": { ... },        // Результат запроса (может быть объектом, массивом или null)
  "error": null             // Сообщение об ошибке (null при успешном запросе)
}
```

## Эндпоинты API

### 1. Языки (Languages)

#### Получение списка всех языков

- **URL**: `/api/languages/`
- **Метод**: `GET`
- **Параметры запроса**:
  - `skip` (int, опционально): Пропуск записей (по умолчанию: 0)
  - `limit` (int, опционально): Ограничение количества (по умолчанию: 100)
- **Успешный ответ**:
  ```json
  {
    "success": true,
    "status": 200,
    "result": [
      {
        "id": "123abc",
        "name_ru": "Английский",
        "name_foreign": "English",
        "created_at": "2023-04-15T12:30:45.123Z",
        "updated_at": "2023-04-15T12:30:45.123Z"
      }
    ],
    "error": null
  }
  ```
- **Ответ при ошибке**:
  ```json
  {
    "success": false,
    "status": 404,
    "result": null,
    "error": "User or language not found"
  }
  ```

#### Получение конкретного языка

- **URL**: `/api/languages/{language_id}`
- **Метод**: `GET`
- **URL-параметры**:
  - `language_id`: ID языка
- **Успешный ответ**:
  ```json
  {
    "success": true,
    "status": 200,
    "result": {
      "id": "123abc",
      "name_ru": "Английский",
      "name_foreign": "English",
      "created_at": "2023-04-15T12:30:45.123Z",
      "updated_at": "2023-04-15T12:30:45.123Z"
    },
    "error": null
  }
  ```
- **Ответ при ошибке**:
  ```json
  {
    "success": false,
    "status": 404,
    "result": null,
    "error": "Language with ID 'nonexistent' not found"
  }
  ```

#### Создание нового языка

- **URL**: `/api/languages/`
- **Метод**: `POST`
- **Заголовки запроса**:
  - `Content-Type: application/json`
- **Тело запроса**:
  ```json
  {
    "name_ru": "Французский",
    "name_foreign": "Français"
  }
  ```
- **Успешный ответ**:
  ```json
  {
    "success": true,
    "status": 201,
    "result": {
      "id": "456def",
      "name_ru": "Французский",
      "name_foreign": "Français",
      "created_at": "2023-04-15T12:30:45.123Z",
      "updated_at": "2023-04-15T12:30:45.123Z"
    },
    "error": null
  }
  ```

#### Обновление языка

- **URL**: `/api/languages/{language_id}`
- **Метод**: `PUT`
- **URL-параметры**:
  - `language_id`: ID языка
- **Заголовки запроса**:
  - `Content-Type: application/json`  
- **Тело запроса**:
  ```json
  {
    "name_ru": "Французский (обновлено)"
  }
  ```
- **Успешный ответ**:
  ```json
  {
    "success": true,
    "status": 200,
    "result": {
      "id": "456def",
      "name_ru": "Французский (обновлено)",
      "name_foreign": "Français",
      "created_at": "2023-04-15T12:30:45.123Z",
      "updated_at": "2023-04-15T13:45:30.456Z"
    },
    "error": null
  }
  ```
- **Ответ при ошибке**:
  ```json
  {
    "success": false,
    "status": 404,
    "result": null,
    "error": "Language with ID '456def' not found"
  }
  ```

#### Удаление языка

- **URL**: `/api/languages/{language_id}`
- **Метод**: `DELETE`
- **URL-параметры**:
  - `language_id`: ID языка
- **Успешный ответ**:
  ```json
  {
    "success": true,
    "status": 200,
    "result": {
      "message": "Language with ID 456def deleted successfully"
    },
    "error": null
  }
  ```
- **Ответ при ошибке**:
  ```json
  {
    "success": false,
    "status": 404,
    "result": null,
    "error": "Language with ID '456def' not found"
  }
  ```

#### Получение слов для конкретного языка

- **URL**: `/api/languages/{language_id}/words`
- **Метод**: `GET`
- **URL-параметры**:
  - `language_id`: ID языка
- **Параметры запроса**:
  - `skip` (int, опционально): Пропуск записей
  - `limit` (int, опционально): Ограничение количества
  - `word_number` (int, опционально): Номер слова для фильтрации
- **Успешный ответ**:
  ```json
  {
    "success": true,
    "status": 200,
    "result": [
      {
        "id": "word123",
        "language_id": "123abc",
        "word_foreign": "hello",
        "translation": "привет",
        "transcription": "həˈləʊ",
        "word_number": 1,
        "sound_file_path": null,
        "created_at": "2023-04-15T12:30:45.123Z",
        "updated_at": "2023-04-15T12:30:45.123Z",
        "user_word_data": {
          "id": "stat123",
          "user_id": "user123",
          "word_id": "word123",
          "language_id": "123abc",
          "hint_phoneticsound": "хэ-лоу",
          "hint_phoneticassociation": "привет-привет",
          "hint_meaning": "приветствие",
          "hint_writing": null,
          "score": 0,
          "is_skipped": false,
          "next_check_date": null,
          "check_interval": 0
        }
        "sound_file_path": null,
        "created_at": "2023-04-15T12:30:45.123Z",
        "updated_at": "2023-04-15T12:30:45.123Z"
      }
    ],
    "error": null
  }
  ```
- **Ответ при ошибке**:
  ```json
  {
    "success": false,
    "status": 404,
    "result": null,
    "error": "Language with ID '123abc' not found"
  }
  ```

#### Получение количества слов для языка

- **URL**: `/api/languages/{language_id}/count`
- **Метод**: `GET`
- **URL-параметры**:
  - `language_id`: ID языка
- **Успешный ответ**:
  ```json
  {
    "success": true,
    "status": 200,
    "result": {
      "count": 1000
    },
    "error": null
  }
  ```
- **Ответ при ошибке**:
  ```json
  {
    "success": false,
    "status": 404,
    "result": null,
    "error": "Language with ID '123abc' not found"
  }
  ```

#### Получение количества активных пользователей для языка

- **URL**: `/api/languages/{language_id}/users/count`
- **Метод**: `GET`
- **URL-параметры**:
  - `language_id`: ID языка
- **Успешный ответ**:
  ```json
  {
    "success": true,
    "status": 200,
    "result": {
      "count": 25
    },
    "error": null
  }
  ```
- **Ответ при ошибке**:
  ```json
  {
    "success": false,
    "status": 404,
    "result": null,
    "error": "Language with ID '123abc' not found"
  }
  ```

#### Загрузка файла со словами

- **URL**: `/api/languages/{language_id}/upload`
- **Метод**: `POST`
- **URL-параметры**:
  - `language_id`: ID языка
- **Заголовки запроса**:
  - `Content-Type: multipart/form-data`
- **Параметры формы**:
  - `file`: Excel-файл со словами
  - `column_word` (int): Индекс колонки с иностранными словами (0-based)
  - `column_translation` (int): Индекс колонки с переводами (0-based)
  - `column_transcription` (int): Индекс колонки с транскрипциями (0-based)
  - `column_number` (int, опционально): Индекс колонки с номерами слов (0-based)
  - `start_row` (int): Начальная строка (1-based)
- **Успешный ответ**:
  ```json
  {
    "success": true,
    "status": 200,
    "result": {
      "filename": "words.xlsx",
      "language_id": "123abc",
      "language_name": "Английский",
      "total_words_processed": 1000,
      "words_added": 800,
      "words_updated": 100,
      "words_skipped": 100,
      "errors": [
        "Row 42: Missing required value",
        "Row 153: Invalid transcription format"
      ]
    },
    "error": null
  }
  ```
- **Ответ при ошибке**:
  ```json
  {
    "success": false,
    "status": 400,
    "result": null,
    "error": "Invalid file format or file not provided"
  }
  ```

#### Экспорт слов языка

- **URL**: `/api/languages/{language_id}/export`
- **Метод**: `GET`
- **URL-параметры**:
  - `language_id`: ID языка
- **Параметры запроса**:
  - `format` (str, опционально): Формат экспорта - "xlsx" (по умолчанию), "csv", "json"
  - `start_word` (int, опционально): Начальный номер слова (включительно)
  - `end_word` (int, опционально): Конечный номер слова (включительно)
- **Описание**: Экспортирует все слова для указанного языка в выбранном формате
- **Структура экспорта**:
  - **Excel/CSV**: Колонки - № | Слово | Перевод | Транскрипция
  - **JSON**: Структурированный JSON с информацией о языке и словах
- **Успешный ответ**: Файл для скачивания с заголовками Content-Disposition
  - **XLSX**: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
  - **CSV**: `text/csv` (с UTF-8 BOM для совместимости с Excel)
  - **JSON**: `application/json`
- **Пример имени файла**: `words_Английский_1-100_20231215_143022.xlsx`
- **Ответ при ошибке**:
  ```json
  {
    "success": false,
    "status": 404,
    "result": null,
    "error": "Language with ID '123abc' not found"
  }
  ```
  ```json
  {
    "success": false,
    "status": 404,
    "result": null,
    "error": "No words found for language 'Английский'"
  }
  ```
  ```json
  {
    "success": false,
    "status": 400,
    "result": null,
    "error": "Error exporting words: [детали ошибки]"
  }
  ```

### 2. Слова (Words)

#### Получение слова по ID

- **URL**: `/api/words/{word_id}`
- **Метод**: `GET`
- **URL-параметры**:
  - `word_id`: ID слова
- **Успешный ответ**:
  ```json
  {
    "success": true,
    "status": 200,
    "result": {
      "id": "word123",
      "language_id": "123abc",
      "word_foreign": "hello",
      "translation": "привет",
      "transcription": "həˈləʊ",
      "word_number": 1,
      "sound_file_path": null,
      "created_at": "2023-04-15T12:30:45.123Z",
      "updated_at": "2023-04-15T12:30:45.123Z"
    },
    "error": null
  }
  ```
- **Ответ при ошибке**:
  ```json
  {
    "success": false,
    "status": 404,
    "result": null,
    "error": "Word with ID 'word123' not found"
  }
  ```

#### Создание нового слова

- **URL**: `/api/words/`
- **Метод**: `POST`
- **Заголовки запроса**:
  - `Content-Type: application/json`
- **Тело запроса**:
  ```json
  {
    "language_id": "123abc",
    "word_foreign": "bonjour",
    "translation": "здравствуйте",
    "transcription": "bɔ̃ʒuʁ",
    "word_number": 1
  }
  ```
- **Успешный ответ**:
  ```json
  {
    "success": true,
    "status": 201,
    "result": {
      "id": "word456",
      "language_id": "123abc",
      "word_foreign": "bonjour",
      "translation": "здравствуйте",
      "transcription": "bɔ̃ʒuʁ",
      "word_number": 1,
      "sound_file_path": null,
      "created_at": "2023-04-15T12:30:45.123Z",
      "updated_at": "2023-04-15T12:30:45.123Z"
    },
    "error": null
  }
  ```

#### Обновление слова

- **URL**: `/api/words/{word_id}`
- **Метод**: `PUT`
- **URL-параметры**:
  - `word_id`: ID слова
- **Заголовки запроса**:
  - `Content-Type: application/json`
- **Тело запроса**:
  ```json
  {
    "translation": "привет",
    "transcription": "bɔ̃ʒuʁ (обновлено)"
  }
  ```
- **Успешный ответ**:
  ```json
  {
    "success": true,
    "status": 200,
    "result": {
      "id": "word456",
      "language_id": "123abc",
      "word_foreign": "bonjour",
      "translation": "привет",
      "transcription": "bɔ̃ʒuʁ (обновлено)",
      "word_number": 1,
      "sound_file_path": null,
      "created_at": "2023-04-15T12:30:45.123Z",
      "updated_at": "2023-04-15T13:45:30.456Z"
    },
    "error": null
  }
  ```
- **Ответ при ошибке**:
  ```json
  {
    "success": false,
    "status": 404,
    "result": null,
    "error": "Word with ID 'word456' not found"
  }
  ```

#### Удаление слова

- **URL**: `/api/words/{word_id}`
- **Метод**: `DELETE`
- **URL-параметры**:
  - `word_id`: ID слова
- **Успешный ответ**:
  ```json
  {
    "success": true,
    "status": 200,
    "result": {
      "message": "Word with ID word456 deleted successfully"
    },
    "error": null
  }
  ```
- **Ответ при ошибке**:
  ```json
  {
    "success": false,
    "status": 404,
    "result": null,
    "error": "Word with ID 'word456' not found"
  }
  ```

### 3. Пользователи (Users)

#### Получение пользователя по Telegram ID

- **URL**: `/api/users`
- **Метод**: `GET`
- **Параметры запроса**:
  - `telegram_id` (int): Telegram ID пользователя
- **Успешный ответ**:
  ```json
  {
    "success": true,
    "status": 200,
    "result": [
      {
        "id": "user123",
        "telegram_id": 123456789,
        "username": "john_doe",
        "first_name": "John",
        "last_name": "Doe",
        "is_admin": false,
        "created_at": "2023-04-15T12:30:45.123Z",
        "updated_at": "2023-04-15T12:30:45.123Z"
      }
    ],
    "error": null
  }
  ```
- **Ответ при отсутствии пользователя**:
  ```json
  {
    "success": true,
    "status": 200,
    "result": [],
    "error": null
  }
  ```

#### Получение количества пользователей

- **URL**: `/api/users/count`
- **Метод**: `GET`
- **Успешный ответ**:
  ```json
  {
    "success": true,
    "status": 200,
    "result": {
      "count": 150
    },
    "error": null
  }
  ```

#### Создание нового пользователя

- **URL**: `/api/users/`
- **Метод**: `POST`
- **Заголовки запроса**:
  - `Content-Type: application/json`
- **Тело запроса**:
  ```json
  {
    "telegram_id": 123456789,
    "username": "john_doe",
    "first_name": "John",
    "last_name": "Doe"
  }
  ```
- **Успешный ответ**:
  ```json
  {
    "success": true,
    "status": 201,
    "result": {
      "id": "user123",
      "telegram_id": 123456789,
      "username": "john_doe",
      "first_name": "John",
      "last_name": "Doe",
      "is_admin": false,
      "created_at": "2023-04-15T12:30:45.123Z",
      "updated_at": "2023-04-15T12:30:45.123Z"
    },
    "error": null
  }
  ```

#### Обновление пользователя

- **URL**: `/api/users/{user_id}`
- **Метод**: `PUT`
- **URL-параметры**:
  - `user_id`: ID пользователя
- **Заголовки запроса**:
  - `Content-Type: application/json`
- **Тело запроса**:
  ```json
  {
    "is_admin": true
  }
  ```
- **Успешный ответ**:
  ```json
  {
    "success": true,
    "status": 200,
    "result": {
      "id": "user123",
      "telegram_id": 123456789,
      "username": "john_doe",
      "first_name": "John",
      "last_name": "Doe",
      "is_admin": true,
      "created_at": "2023-04-15T12:30:45.123Z",
      "updated_at": "2023-04-15T13:45:30.456Z"
    },
    "error": null
  }
  ```
- **Ответ при ошибке**:
  ```json
  {
    "success": false,
    "status": 404,
    "result": null,
    "error": "User with ID 'user123' not found"
  }
  ```

### 4. Данные пользователя по словам (User Word Data)

#### Получение данных пользователя по слову

- **URL**: `/api/users/{user_id}/word_data/{word_id}`
- **Метод**: `GET`
- **URL-параметры**:
  - `user_id`: ID пользователя
  - `word_id`: ID слова
- **Успешный ответ**:
  ```json
  {
    "success": true,
    "status": 200,
    "result": {
      "id": "stat123",
      "user_id": "user123",
      "word_id": "word456",
      "language_id": "123abc",
      "hint_phoneticsound": "бон-жур",
      "hint_phoneticassociation": "бонус за журнал",
      "hint_meaning": "приветствие при встрече",
      "hint_writing": null,
      "score": 1,
      "is_skipped": false,
      "next_check_date": "2023-04-20T00:00:00.000Z",
      "check_interval": 4,
      "created_at": "2023-04-15T12:30:45.123Z",
      "updated_at": "2023-04-15T12:30:45.123Z"
    },
    "error": null
  }
  ```
- **Ответ при отсутствии данных**:
  ```json
  {
    "success": true,
    "status": 200,
    "result": null,
    "error": null
  }
  ```

#### Создание данных слова для пользователя

- **URL**: `/api/users/{user_id}/word_data`
- **Метод**: `POST`
- **URL-параметры**:
  - `user_id`: ID пользователя
- **Заголовки запроса**:
  - `Content-Type: application/json`
- **Тело запроса**:
  ```json
  {
    "word_id": "word456",
    "language_id": "123abc",
    "hint_phoneticassociation": "моя подсказка",
    "score": 0,
    "is_skipped": false
  }
  ```
- **Успешный ответ**:
  ```json
  {
    "success": true,
    "status": 201,
    "result": {
      "id": "stat123",
      "user_id": "user123",
      "word_id": "word456",
      "language_id": "123abc",
      "hint_phoneticsound": null,
      "hint_phoneticassociation": "моя подсказка",
      "hint_meaning": null,
      "hint_writing": null,
      "score": 0,
      "is_skipped": false,
      "next_check_date": null,
      "check_interval": 0,
      "created_at": "2023-04-15T12:30:45.123Z",
      "updated_at": "2023-04-15T12:30:45.123Z"
    },
    "error": null
  }
  ```

#### Обновление данных слова для пользователя

- **URL**: `/api/users/{user_id}/word_data/{word_id}`
- **Метод**: `PUT`
- **URL-параметры**:
  - `user_id`: ID пользователя
  - `word_id`: ID слова
- **Заголовки запроса**:
  - `Content-Type: application/json`
- **Тело запроса**:
  ```json
  {
    "score": 1,
    "check_interval": 2,
    "hint_phoneticassociation": "новая подсказка"
  }
  ```
- **Успешный ответ**:
  ```json
  {
    "success": true,
    "status": 200,
    "result": {
      "id": "stat123",
      "user_id": "user123",
      "word_id": "word456",
      "language_id": "123abc",
      "hint_phoneticsound": null,
      "hint_phoneticassociation": "новая подсказка",
      "hint_meaning": null,
      "hint_writing": null,
      "score": 1,
      "is_skipped": false,
      "next_check_date": "2023-04-17T00:00:00.000Z",
      "check_interval": 2,
      "created_at": "2023-04-15T12:30:45.123Z",
      "updated_at": "2023-04-15T13:45:30.456Z"
    },
    "error": null
  }
  ```
- **Ответ при ошибке**:
  ```json
  {
    "success": false,
    "status": 404,
    "result": null,
    "error": "User word data not found"
  }
  ```

### 5. Прогресс (Progress)

#### Получение прогресса пользователя для языка

- **URL**: `/api/users/{user_id}/languages/{language_id}/progress`
- **Метод**: `GET`
- **URL-параметры**:
  - `user_id`: ID пользователя
  - `language_id`: ID языка
- **Успешный ответ**:
  ```json
  {
    "success": true,
    "status": 200,
    "result": {
      "user_id": "user123",
      "language_id": "123abc",
      "language_name_ru": "Английский",
      "language_name_foreign": "English",
      "total_words": 1000,
      "words_studied": 100,
      "words_known": 50,
      "words_skipped": 10,
      "progress_percentage": 5.0,
      "last_study_date": "2023-04-15T12:30:45.123Z"
    },
    "error": null
  }
  ```

### 7. Настройки пользователя (User Language Settings)

#### Получение настроек пользователя для языка

- **URL**: `/api/users/{user_id}/languages/{language_id}/settings`
- **Метод**: `GET`
- **URL-параметры**:
  - `user_id`: ID пользователя
  - `language_id`: ID языка
- **Успешный ответ**:
  ```json
  {
    "success": true,
    "status": 200,
    "result": {
      "start_word": 5,
      "skip_marked": true,
      "use_check_date": false,
      "show_hints": true,
      "id": "60f1e5b3c7e33e001f5c7b1a",
      "user_id": "60f1e5b3c7e33e001f5c7b1b",
      "language_id": "60f1e5b3c7e33e001f5c7b1c",
      "created_at": "2023-07-16T12:30:45.123Z",
      "updated_at": "2023-07-16T13:45:30.456Z"
    },
    "error": null
  }
  ```
- **Примечания**:
  - Если настройки не найдены, возвращаются значения по умолчанию
  - Возвращается ошибка 404, если пользователь или язык не найдены

#### Обновление настроек пользователя для языка

- **URL**: `/api/users/{user_id}/languages/{language_id}/settings`
- **Метод**: `PUT`
- **URL-параметры**:
  - `user_id`: ID пользователя
  - `language_id`: ID языка
- **Заголовки запроса**:
  - `Content-Type: application/json`
- **Тело запроса**:
  ```json
  {
    "start_word": 5,
    "skip_marked": true,
    "use_check_date": false,
    "show_hints": true
  }
  ```
- **Успешный ответ**:
  ```json
  {
    "success": true,
    "status": 200,
    "result": {
      "start_word": 5,
      "skip_marked": true,
      "use_check_date": false,
      "show_hints": true,
      "id": "60f1e5b3c7e33e001f5c7b1a",
      "user_id": "60f1e5b3c7e33e001f5c7b1b",
      "language_id": "60f1e5b3c7e33e001f5c7b1c",
      "created_at": "2023-07-16T12:30:45.123Z",
      "updated_at": "2023-07-16T13:45:30.456Z"
    },
    "error": null
  }
  ```
- **Примечания**:
  - Если настройки не существуют, они будут созданы (upsert behavior)
  - Можно обновлять только нужные поля, остальные оставить неизменными
  - Возвращается ошибка 404, если пользователь или язык не найдены

#### Получение всех настроек пользователя

- **URL**: `/api/users/{user_id}/settings`
- **Метод**: `GET`
- **URL-параметры**:
  - `user_id`: ID пользователя
- **Успешный ответ**:
  ```json
  {
    "success": true,
    "status": 200,
    "result": [
      {
        "start_word": 5,
        "skip_marked": true,
        "use_check_date": false,
        "show_hints": true,
        "id": "60f1e5b3c7e33e001f5c7b1a",
        "user_id": "60f1e5b3c7e33e001f5c7b1b",
        "language_id": "60f1e5b3c7e33e001f5c7b1c",
        "created_at": "2023-07-16T12:30:45.123Z",
        "updated_at": "2023-07-16T13:45:30.456Z"
      },
      {
        "start_word": 1,
        "skip_marked": false,
        "use_check_date": true,
        "show_hints": true,
        "id": "60f1e5b3c7e33e001f5c7b1d",
        "user_id": "60f1e5b3c7e33e001f5c7b1b",
        "language_id": "60f1e5b3c7e33e001f5c7b1e",
        "created_at": "2023-07-16T12:30:45.123Z",
        "updated_at": "2023-07-16T13:45:30.456Z"
      }
    ],
    "error": null
  }
  ```
- **Примечания**:
  - Возвращает пустой список, если у пользователя нет настроек
  - Возвращается ошибка 404, если пользователь не найден

### 6. Слова для изучения (Study Words)

#### Получение слов для изучения

- **URL**: `/api/users/{user_id}/languages/{language_id}/study`
- **Метод**: `GET`
- **URL-параметры**:
  - `user_id`: ID пользователя
  - `language_id`: ID языка
- **Параметры запроса**:
  - `start_word` (int, опционально): Начальный номер слова (по умолчанию: 1)
  - `skip_marked` (bool, опционально): Пропускать помеченные слова (по умолчанию: false)
  - `use_check_date` (bool, опционально): Учитывать дату проверки (по умолчанию: true)
  - `limit` (int, опционально): Максимальное количество слов (по умолчанию: 100)
- **Успешный ответ**:
  ```json
  {
    "success": true,
    "status": 200,
    "result": [
      {
        "id": "word123",
        "language_id": "123abc",
        "word_foreign": "hello",
        "translation": "привет",
        "transcription": "həˈləʊ",
        "word_number": 1,
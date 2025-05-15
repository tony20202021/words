# Настройка MongoDB для проекта

## Содержание
1. [Введение](#введение)
2. [Способы установки MongoDB](#способы-установки-mongodb)
3. [Настройка MongoDB для проекта](#настройка-mongodb-для-проекта)
4. [Запуск и остановка MongoDB](#запуск-и-остановка-mongodb)
5. [Инициализация базы данных](#инициализация-базы-данных)
6. [Управление MongoDB](#управление-mongodb)
7. [Структура базы данных](#структура-базы-данных)
8. [Устранение проблем](#устранение-проблем)

## Введение

MongoDB используется в качестве основной базы данных проекта Language Learning Bot. Этот документ описывает процессы установки, настройки и управления MongoDB для правильной работы приложения.

## Способы установки MongoDB

### 1. Установка в пользовательский каталог (без прав суперпользователя)

```bash
# Создание директорий для MongoDB
mkdir -p ~/mongodb/data ~/mongodb/log ~/mongodb/config ~/mongodb/bin

# Переход в директорию для загрузки
cd ~/Downloads

# Скачивание MongoDB (для Ubuntu 22.04, x86_64)
wget https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-ubuntu2204-7.0.5.tgz

# Распаковка архива
tar -zxvf mongodb-linux-x86_64-ubuntu2204-7.0.5.tgz

# Копирование исполняемых файлов
cp -R mongodb-linux-x86_64-ubuntu2204-7.0.5/bin/* ~/mongodb/bin/

# Добавление MongoDB в PATH
echo 'export PATH=~/mongodb/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
```

### 2. Установка через менеджер пакетов (с правами суперпользователя)

#### Для Ubuntu/Debian:

```bash
# Импорт публичного ключа MongoDB
wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | sudo apt-key add -

# Создание файла источника пакетов
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu $(lsb_release -cs)/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list

# Обновление базы пакетов
sudo apt update

# Установка MongoDB
sudo apt install -y mongodb-org

# Запуск MongoDB
sudo systemctl start mongod

# Включение автозапуска при старте системы
sudo systemctl enable mongod
```

### 3. Использование Docker

```bash
# Запуск MongoDB в контейнере
docker run --name mongodb -d -p 27017:27017 -v ~/mongodb/data:/data/db mongo:7.0.5
```

## Настройка MongoDB для проекта

### Создание конфигурационного файла MongoDB

При запуске MongoDB с помощью скрипта `start_1_db.sh` автоматически создается конфигурационный файл `~/mongodb/config/mongod.conf`. Вы также можете создать его вручную:

```bash
cat > ~/mongodb/config/mongod.conf << EOL
storage:
  dbPath: $HOME/mongodb/data
systemLog:
  destination: file
  path: $HOME/mongodb/log/mongod.log
  logAppend: true
net:
  bindIp: 127.0.0.1
  port: 27017
EOL
```

### Настройка переменных окружения

Для правильной работы скриптов проекта необходимо настроить переменные окружения MongoDB:

1. Создайте файл `.env` в корне проекта на основе `.env.example`:
   ```bash
   cp .env.example .env
   ```

2. Отредактируйте файл, добавив или проверив настройки MongoDB:
   ```
   MONGODB_HOST=localhost
   MONGODB_PORT=27017
   MONGODB_DB_NAME=language_learning_bot
   ```

3. Для загрузки этих переменных в окружение используйте скрипт `run_export_env.sh`:
   ```bash
   source ./run_export_env.sh
   ```

## Запуск и остановка MongoDB

### Запуск MongoDB с помощью скрипта проекта

В проекте предусмотрен скрипт `start_1_db.sh` для автоматического запуска MongoDB:

```bash
# Сделать скрипт исполняемым
chmod +x start_1_db.sh

# Запустить MongoDB
./start_1_db.sh
```

Скрипт выполняет следующие операции:
1. Загружает настройки из файла `.env`
2. Проверяет, запущен ли уже MongoDB
3. Создает необходимые директории, если они отсутствуют
4. Создает или обновляет конфигурационный файл
5. Запускает MongoDB как фоновый процесс

### Ручной запуск MongoDB

Вы можете запустить MongoDB вручную с помощью следующих команд:

```bash
# Запуск с конфигурационным файлом
~/mongodb/bin/mongod --config ~/mongodb/config/mongod.conf --fork

# Проверка запуска
ps aux | grep mongod
```

### Остановка MongoDB

Для корректной остановки MongoDB используйте следующие команды:

```bash
# Остановка через MongoDB Shell
~/mongodb/bin/mongosh --eval "db.adminCommand({ shutdown: 1 })"

# Альтернативный вариант через kill
pkill -f mongod
```

## Инициализация базы данных

После запуска MongoDB необходимо инициализировать базу данных:

```bash
# Запуск скрипта инициализации
python scripts/init_db.py

# Заполнение тестовыми данными (опционально)
python scripts/seed_data.py
```

## Управление MongoDB

### Подключение к MongoDB Shell

Для прямого взаимодействия с MongoDB используйте MongoDB Shell:

```bash
# Запуск MongoDB Shell
~/mongodb/bin/mongosh

# Подключение к базе данных проекта
use language_learning_bot

# Просмотр доступных коллекций
show collections

# Пример запроса к коллекции
db.languages.find()
```

### Резервное копирование базы данных

Для создания резервной копии базы данных используйте утилиту `mongodump`:

```bash
# Создание директории для резервных копий
mkdir -p backup

# Создание резервной копии
~/mongodb/bin/mongodump --host $MONGODB_HOST --port $MONGODB_PORT --db $MONGODB_DB_NAME --out backup/$(date +%Y%m%d)
```

### Восстановление из резервной копии

Для восстановления базы данных из резервной копии используйте утилиту `mongorestore`:

```bash
# Восстановление из резервной копии
~/mongodb/bin/mongorestore --host $MONGODB_HOST --port $MONGODB_PORT --db $MONGODB_DB_NAME backup/YYYYMMDD/$MONGODB_DB_NAME
```

## Структура базы данных

В проекте используются следующие коллекции MongoDB:

### 1. Коллекция `languages`

Хранит информацию о доступных языках.

```json
{
  "_id": ObjectId("..."),            // Уникальный идентификатор
  "name_ru": "Английский",           // Название на русском
  "name_foreign": "English",         // Название на оригинальном языке
  "created_at": ISODate("..."),      // Дата создания
  "updated_at": ISODate("...")       // Дата обновления
}
```

### 2. Коллекция `words`

Хранит слова для изучения.

```json
{
  "_id": ObjectId("..."),            // Уникальный идентификатор
  "language_id": ObjectId("..."),    // Ссылка на язык
  "word_foreign": "hello",           // Слово на иностранном языке
  "translation": "привет",           // Перевод на русский
  "transcription": "həˈləʊ",         // Транскрипция
  "word_number": 1,                  // Номер в частотном списке
  "sound_file_path": null,           // Путь к аудиофайлу (если есть)
  "created_at": ISODate("..."),      // Дата создания
  "updated_at": ISODate("...")       // Дата обновления
}
```

### 3. Коллекция `users`

Хранит информацию о пользователях.

```json
{
  "_id": ObjectId("..."),            // Уникальный идентификатор
  "telegram_id": 123456789,          // ID пользователя в Telegram
  "username": "username",            // Имя пользователя в Telegram
  "first_name": "John",              // Имя
  "last_name": "Doe",                // Фамилия
  "is_admin": false,                 // Флаг администратора
  "created_at": ISODate("..."),      // Дата создания
  "updated_at": ISODate("...")       // Дата обновления
}
```

### 4. Коллекция `user_statistics`

Хранит статистику изучения слов пользователями.

```json
{
  "_id": ObjectId("..."),            // Уникальный идентификатор
  "user_id": ObjectId("..."),        // Ссылка на пользователя
  "word_id": ObjectId("..."),        // Ссылка на слово
  "language_id": ObjectId("..."),    // Ссылка на язык
  "hint_syllables": "хэл-лоу",       // Подсказка по слогам
  "hint_association": "...",         // Ассоциативная подсказка
  "hint_meaning": "...",             // Подсказка по значению
  "hint_writing": null,              // Подсказка по написанию
  "score": 0,                        // Оценка (0 - не знаю, 1 - знаю)
  "is_skipped": false,               // Флаг пропуска слова
  "next_check_date": null,           // Дата следующей проверки
  "check_interval": 0,               // Интервал между проверками (в днях)
  "created_at": ISODate("..."),      // Дата создания
  "updated_at": ISODate("...")       // Дата обновления
}
```

### 5. Коллекция `user_language_settings`

Хранит настройки пользователя для каждого языка.

```json
{
  "_id": ObjectId("..."),            // Уникальный идентификатор записи
  "user_id": ObjectId("..."),        // Ссылка на пользователя
  "language_id": ObjectId("..."),    // Ссылка на язык
  "start_word": 1,                   // Номер слова, с которого начать изучение (по умолчанию: 1)
  "skip_marked": false,              // Пропускать ли помеченные слова (по умолчанию: false)
  "use_check_date": true,            // Учитывать ли дату следующей проверки (по умолчанию: true)
  "show_hints": true,                // Отображать ли кнопки подсказок (по умолчанию: true)
  "created_at": ISODate("..."),      // Дата создания
  "updated_at": ISODate("...")       // Дата обновления
}
```

**Индексы**:
- Составной уникальный индекс по полям `user_id` и `language_id` - обеспечивает уникальность настроек для каждой комбинации "пользователь-язык"

**Преимущества новой коллекции `user_language_settings`**:
1. Постоянное хранение настроек между сеансами работы бота
2. Независимые настройки для каждого языка пользователя
3. Возможность централизованного управления настройками
4. Сохранение настроек при перезапуске бота или переустановке приложения пользователем

## Устранение проблем

### MongoDB не запускается

Если MongoDB не запускается, проверьте следующее:

1. Логи MongoDB:
   ```bash
   cat ~/mongodb/log/mongod.log
   ```

2. Наличие директорий для данных и логов:
   ```bash
   ls -la ~/mongodb/data
   ls -la ~/mongodb/log
   ```

3. Права доступа к директориям:
   ```bash
   chmod 755 ~/mongodb/data
   chmod 755 ~/mongodb/log
   ```

4. Занятость порта MongoDB:
   ```bash
   lsof -i :27017
   ```

### Ошибки соединения

Если возникают ошибки при подключении к MongoDB:

1. Проверьте, запущен ли процесс MongoDB:
   ```bash
   ps aux | grep mongod
   ```

2. Проверьте настройки подключения в `.env` файле:
   ```bash
   cat .env | grep MONGODB
   ```

3. Проверьте доступность порта MongoDB:
   ```bash
   telnet localhost 27017
   ```

4. Проверьте настройки брандмауэра:
   ```bash
   sudo iptables -L | grep 27017
   ```

### Сбои при инициализации базы данных

Если возникают проблемы при инициализации базы данных:

1. Проверьте, что MongoDB запущена
2. Убедитесь, что переменные окружения правильно настроены
3. Проверьте права доступа к директории проекта
4. Изучите логи приложения для выявления ошибок

### Медленная работа MongoDB

Если MongoDB работает медленно:

1. Проверьте загрузку системы и доступность ресурсов
2. Убедитесь, что на диске достаточно свободного места
3. Проверьте логи на наличие сообщений о проблемах с производительностью
4. Рассмотрите возможность оптимизации индексов базы данных
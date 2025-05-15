# Руководство по установке

## Содержание
1. [Предварительные требования](#предварительные-требования)
2. [Быстрая установка](#быстрая-установка)
3. [Пошаговая установка](#пошаговая-установка)
   - [Получение исходного кода](#получение-исходного-кода)
   - [Настройка окружения](#настройка-окружения)
   - [Установка MongoDB](#установка-mongodb)
   - [Конфигурация проекта](#конфигурация-проекта)
   - [Установка зависимостей](#установка-зависимостей)
   - [Инициализация базы данных](#инициализация-базы-данных)
4. [Варианты установки MongoDB](#варианты-установки-mongodb)
5. [Проверка установки](#проверка-установки)
6. [Устранение проблем](#устранение-проблем)
7. [Следующие шаги](#следующие-шаги)

## Предварительные требования

Для работы с проектом требуются:

- Python 3.8 или выше
- Conda (для управления окружением)
- Git
- Доступ к Telegram Bot API (токен)
- Около 500 МБ свободного дискового пространства
- FFmpeg (для обработки аудиофайлов)
- PyTorch и зависимости для модуля распознавания речи Whisper

## Быстрая установка

Для опытных пользователей, вот краткая последовательность команд для установки:

```bash
# Клонирование репозитория
git clone https://github.com/username/language-learning-bot.git
cd language-learning-bot

# Настройка окружения с Conda
conda env create -f environment.yml
conda activate language-learning-bot

# Копирование и настройка .env файла
cp .env.example .env
# Отредактируйте .env добавив TELEGRAM_BOT_TOKEN

# Установка и запуск MongoDB 
./start_1_db.sh

# Инициализация базы данных
python scripts/init_db.py

# Опционально: заполнение тестовыми данными
python scripts/seed_data.py

# Запуск бэкенда и фронтенда
./start_2_backend.sh
./start_3_frontend.sh
```

## Пошаговая установка

### Получение исходного кода

Клонируйте репозиторий проекта:

```bash
git clone https://github.com/username/language-learning-bot.git
cd language-learning-bot
```


### Настройка окружения

#### С использованием Conda (рекомендуется)

Conda обеспечивает изолированное окружение со всеми необходимыми зависимостями:

```bash
# Создание окружения из файла environment.yml
conda env create -f environment.yml

# Активация окружения
conda activate language-learning-bot
```

#### Вручную с использованием pip

Если вы предпочитаете не использовать Conda:

```bash
# Создание виртуального окружения
python -m venv venv

# Активация окружения
# Для Linux/Mac:
source venv/bin/activate
# Для Windows:
venv\Scripts\activate

# Установка зависимостей
pip install -r requirements.txt
```

### Установка MongoDB

Для работы проекта требуется MongoDB версии 5.0 или выше. Выберите один из способов установки:

#### Вариант 1: Использование скрипта start_1_db.sh (рекомендуется)

Самый простой способ, который автоматически настраивает и запускает MongoDB:

```bash
# Сделать скрипт исполняемым
chmod +x start_1_db.sh

# Запустить MongoDB
./start_1_db.sh
```

#### Вариант 2: Ручная установка

См. раздел [Варианты установки MongoDB](#варианты-установки-mongodb) для других способов установки.

### Конфигурация проекта

#### Создание файла .env

Создайте файл `.env` на основе `.env.example`:

```bash
cp .env.example .env
```

Отредактируйте файл `.env` и установите необходимые параметры:

```ini
# Настройки MongoDB
MONGODB_HOST=localhost
MONGODB_PORT=27017
MONGODB_DB_NAME=language_learning_bot

# Настройки Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

#### Настройка Hydra конфигурации

Проект использует Hydra для управления конфигурацией. Основные файлы находятся в:

- `frontend/conf/config/`
- `backend/conf/config/`

Важные файлы для настройки:

1. **frontend/conf/config/bot.yaml** - добавьте ваш Telegram Bot токен:
   ```yaml
   token: "YOUR_TELEGRAM_BOT_TOKEN"
   ```

2. **frontend/conf/config/api.yaml** - проверьте URL подключения к бэкенду:
   ```yaml
   base_url: "http://localhost:8500"
   ```

3. **backend/conf/config/database.yaml** - настройки MongoDB:
   ```yaml
   mongodb:
     host: "localhost"
     port: 27017
     db_name: "language_learning_bot"
   ```

### Установка зависимостей

Если вы используете Conda, зависимости уже установлены при создании окружения. В противном случае:

```bash
pip install -r requirements.txt
```

### Инициализация базы данных

После установки и настройки необходимо инициализировать базу данных:

```bash
# Проверьте, что MongoDB запущена
# Если нет, запустите ее
./start_1_db.sh

# Инициализация базы данных
python scripts/init_db.py

# Заполнение базы тестовыми данными (опционально)
python scripts/seed_data.py
```

## Варианты установки MongoDB

### Способ 1: Установка в пользовательский каталог (без прав суперпользователя)

```bash
# Создание директорий для MongoDB
mkdir -p ~/mongodb/data ~/mongodb/log ~/mongodb/config ~/mongodb/bin

# Скачивание MongoDB (для Ubuntu 22.04, x86_64)
cd ~/Downloads
wget https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-ubuntu2204-7.0.5.tgz

# Распаковка архива
tar -zxvf mongodb-linux-x86_64-ubuntu2204-7.0.5.tgz

# Копирование исполняемых файлов
cp -R mongodb-linux-x86_64-ubuntu2204-7.0.5/bin/* ~/mongodb/bin/

# Добавление MongoDB в PATH
echo 'export PATH=~/mongodb/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
```

### Способ 2: Установка через менеджер пакетов (с правами суперпользователя)

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

### Способ 3: Использование Docker

```bash
# Запуск MongoDB в контейнере
docker run --name mongodb -d -p 27017:27017 -v ~/mongodb/data:/data/db mongo:7.0.5
```

## Проверка установки

После завершения установки необходимо проверить, что все компоненты работают корректно:

### 1. Проверка MongoDB

```bash
# Проверка запущена ли MongoDB
ps aux | grep mongod

# Подключение к MongoDB
mongosh
```

Если MongoDB работает, вы увидите приглашение MongoDB Shell.

### 2. Проверка бэкенда

```bash
# Запуск бэкенда
./start_2_backend.sh

# Проверка доступности API
curl http://localhost:8500/api/health
```

Должен вернуться положительный ответ в формате JSON.

### 3. Проверка фронтенда

```bash
# Запуск фронтенда
./start_3_frontend.sh
```

Проверьте, что бот отвечает на команду `/start` в Telegram.

## Устранение проблем

### MongoDB не запускается

**Проблема**: Ошибки при запуске MongoDB с использованием скрипта `start_1_db.sh`.

**Решение**:
1. Проверьте наличие директорий:
   ```bash
   ls -la ~/mongodb/data
   ls -la ~/mongodb/log
   ```

2. Проверьте права доступа:
   ```bash
   chmod 755 ~/mongodb/data
   chmod 755 ~/mongodb/log
   ```

3. Проверьте логи MongoDB:
   ```bash
   cat ~/mongodb/log/mongod.log
   ```

### Бэкенд не запускается

**Проблема**: Ошибки при запуске бэкенда.

**Решение**:
1. Проверьте подключение к MongoDB:
   ```bash
   mongosh --eval "db.stats()"
   ```

2. Проверьте конфигурацию в `.env`:
   ```bash
   cat .env | grep MONGODB
   ```

3. Проверьте порт бэкенда:
   ```bash
   lsof -i :8500
   ```

### Фронтенд не запускается

**Проблема**: Ошибки при запуске фронтенда.

**Решение**:
1. Проверьте токен Telegram бота:
   ```bash
   cat frontend/conf/config/bot.yaml | grep token
   ```

2. Проверьте доступность бэкенда:
   ```bash
   curl http://localhost:8500/api/health
   ```

## Следующие шаги

После успешной установки:

1. [Руководство по запуску](../running/running_guide.md) - запуск и управление компонентами 
2. [Функциональность бота](../functionality/bot_commands.md) - команды и возможности бота
3. [API-интерфейс](../api/api_reference.md) - документация по API-клиенту

Для разработчиков:
1. [Тестирование](../development/testing_guide.md) - как запускать и писать тесты
2. [Конфигурация](../development/configuration.md) - детали конфигурации с Hydra
3. [Структура проекта](../development/directory_structure.md) - организация файлов и директорий


Заменим раздел по установке FFmpeg на следующий:
markdown### Установка FFmpeg без прав администратора

Для работы с голосовыми сообщениями требуется FFmpeg. Поскольку у вас нет прав sudo, мы будем использовать один из следующих подходов:

#### Вариант 1: Использование imageio-ffmpeg (рекомендуется)

imageio-ffmpeg включает предкомпилированные бинарники FFmpeg и не требует системной установки:

```bash
# Активация окружения
conda activate language-learning-bot

# Установка через pip
pip install imageio-ffmpeg
Вариант 2: Компиляция FFmpeg из исходников
Если вам нужен полный контроль над FFmpeg, его можно скомпилировать из исходников:
bash# Создание директории для сборки
mkdir -p ~/ffmpeg_build && cd ~/ffmpeg_build

# Скачивание исходников
wget https://ffmpeg.org/releases/ffmpeg-4.4.tar.bz2
tar xjf ffmpeg-4.4.tar.bz2
cd ffmpeg-4.4

# Конфигурация с указанием директории установки в домашнем каталоге
./configure --prefix=$HOME/.local --enable-shared --disable-static

# Компиляция и установка
make -j$(nproc)
make install

# Добавление в PATH
echo 'export PATH=$HOME/.local/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
Вариант 3: Использование conda для установки FFmpeg
Если вы используете conda, можно установить FFmpeg через conda без прав sudo:
bashconda install -c conda-forge ffmpeg
Проверка установки FFmpeg
После установки FFmpeg любым из описанных способов, проверьте его наличие:
bash# Проверка доступности FFmpeg
ffmpeg -version
Система автоматически найдет установленный FFmpeg при запуске бота.

### 4.2. Обновление environment_setup.md

```markdown
### Настройка распознавания речи

Проект использует модель Whisper от OpenAI для распознавания голосовых сообщений, и для этого требуется FFmpeg.

#### Настройка путей для FFmpeg

Система автоматически ищет FFmpeg в следующих местах:
1. Системный путь (PATH)
2. Пакет imageio-ffmpeg (если установлен)
3. Директории conda/virtualenv
4. Пользовательские директории (~/.local/bin, ~/bin)

Если FFmpeg не обнаружен автоматически, вы можете указать путь вручную:

```yaml
# В файле frontend/conf/config/bot.yaml
voice_recognition:
  ffmpeg_path: "/path/to/your/ffmpeg"  # Укажите полный путь к FFmpeg
  model_size: "small"                  # Размер модели Whisper
  language: "ru"                      # Язык распознавания
  temp_dir: "temp"                    # Директория для временных файлов
Настройка модели Whisper
Вы можете выбрать размер модели Whisper в зависимости от ваших вычислительных ресурсов:
МодельРазмерТочностьСкоростьРекомендуется дляtiny~150MBНизкаяВысокаяСлабые устройстваbase~300MBСредняяСредняяНоутбуки/ПК с ограниченными ресурсамиsmall~500MBХорошаяСредняяБольшинство случаев (по умолчанию)medium~1.5GBВысокаяНизкаяМощные ПКlarge~3GBОчень высокаяОчень низкаяСерверы
При первом запуске модель Whisper будет автоматически загружена. Модель кэшируется для последующего использования.
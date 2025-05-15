# Language Learning Bot

Language Learning Bot - это Telegram-бот для эффективного изучения иностранных языков с использованием системы интервального повторения и персонализированных подсказок.

## Возможности

- 📚 Изучение слов с помощью системы интервального повторения
- 🔄 Настройка процесса обучения под свои потребности
- 🔤 Создание персонализированных подсказок для запоминания
- 📊 Отслеживание прогресса изучения
- 🌐 Поддержка множества языков
- 👨‍💼 Административный интерфейс для управления контентом

## Архитектура

Проект построен на модульной архитектуре с разделением на два независимых сервиса:

- **Frontend**: Telegram-бот на Python с использованием aiogram
- **Backend**: REST API на FastAPI с MongoDB в качестве базы данных

## Быстрый старт

### Требования

- Python 3.8+
- MongoDB 5.0+
- Telegram Bot API ключ

### Установка и запуск

1. Клонирование репозитория:
   ```bash
   git clone https://github.com/username/language-learning-bot.git
   cd language-learning-bot
   ```

2. Настройка окружения:
   ```bash
   conda env create -f environment.yml
   conda activate language-learning-bot
   ```

3. Конфигурация:
   ```bash
   cp .env.example .env
   # Отредактируйте .env и добавьте ваш TELEGRAM_BOT_TOKEN
   ```

4. Запуск сервисов:
   ```bash
   ./start_1_db.sh          # Запуск MongoDB
   ./start_2_backend.sh     # Запуск бэкенда
   ./start_3_frontend.sh    # Запуск фронтенда (Telegram-бота)
   ```

5. Откройте бота в Telegram и начните обучение!

## Документация

Подробная документация доступна в директории `docs/`:

- [Руководство по установке](docs/installation/installation_guide.md)
- [Запуск и управление](docs/running/running_guide.md)
- [Функциональность бота](docs/functionality/bot_commands.md)
- [API-интерфейс](docs/api/api_reference.md)
- [Разработка и тестирование](docs/development/testing_guide.md)

## Лицензия

MIT

## Автор

Anton Mikhalev  
[@Anton_Mikhalev](https://t.me/Anton_Mikhalev)  
anton.v.mikhalev@gmail.com
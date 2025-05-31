# Language Learning Bot

Language Learning Bot - это Telegram-бот для эффективного изучения иностранных языков с использованием системы интервального повторения и персонализированных подсказок.

## Возможности

- 📚 Изучение слов с помощью системы интервального повторения
- 🔄 Настройка процесса обучения под свои потребности
- 🔤 Создание персонализированных подсказок для запоминания
- 💡 **Индивидуальные настройки для каждого типа подсказок**
- 🖼️ **Генерация крупных изображений слов с Unicode поддержкой**
- 📊 Отслеживание прогресса изучения
- 🌐 Поддержка множества языков
- 👨‍💼 Административный интерфейс для управления контентом

## Архитектура

Проект построен на модульной архитектуре с разделением на два независимых сервиса:

- **Frontend**: Telegram-бот на Python с использованием aiogram 3.x
- **Backend**: REST API на FastAPI с MongoDB в качестве базы данных

## Быстрый старт

### Требования

- Python 3.8+
- MongoDB 5.0+
- Telegram Bot API ключ
- Pillow (для генерации изображений)

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

## Тестирование

Проект имеет обширное тестовое покрытие, включающее:

- Модульные тесты компонентов фронтенда
- Тесты обработчиков пользовательских команд
- Тесты обработчиков административных команд
- Тесты API-клиента
- Тесты взаимодействия с базой данных
- Сценарные тесты различных пользовательских сценариев

Запуск тестов осуществляется через скрипт `run_tests.sh`:

```bash
# Запуск всех тестов
./run_tests.sh

# Запуск тестов с отчетом о покрытии
./run_tests.sh --coverage
```

## Документация

Подробная документация доступна в директории `docs/`:

- [Руководство по установке](docs/installation/installation_guide.md)
- [Запуск и управление](docs/running/running_guide.md)
- [Функциональность бота](docs/functionality/bot_commands.md)
- [API-интерфейс](docs/api/api_reference.md)
- [Разработка и тестирование](docs/development/testing_guide.md)
- [Архитектура системы](docs/architecture.md)

## Технические особенности

### Система индивидуальных настроек подсказок

Каждый пользователь может настроить отображение подсказок индивидуально:

```python
# Пример настроек подсказок пользователя
{
    "show_hint_meaning": True,              # Ассоциации на русском
    "show_hint_phoneticassociation": True,  # Фонетические ассоциации  
    "show_hint_phoneticsound": True,        # Звучание по слогам
    "show_hint_writing": True,              # Подсказки написания
}
```

### Система генерации изображений слов

**НОВОЕ**: Автоматическая генерация крупных изображений слов с полной поддержкой Unicode:

- **Поддержка всех языков**: включая китайские иероглифы, арабский, хинди и другие
- **Автоподбор размера шрифта**: если текст не помещается, размер автоматически уменьшается
- **Умное позиционирование**: центрирование по горизонтали и вертикали
- **Настраиваемый дизайн**: цвета, размеры, шрифты через конфигурацию

```yaml
# Конфигурация в bot.yaml
word_images:
  enabled: true
  width: 800
  height: 400
  fonts:
    word_size: 240
    transcription_size: 240
  colors:
    background: [255, 255, 255]
    text: [50, 50, 50]
```

#### Поддержка Unicode

Система автоматически ищет Unicode шрифты:

**Windows:**
- `msyh.ttc` (Microsoft YaHei)
- `simsun.ttc` (SimSun)
- `arial.ttf` (Arial)

**macOS:**
- `/System/Library/Fonts/PingFang.ttc` (PingFang SC)
- `/System/Library/Fonts/Arial.ttf`
- `/System/Library/Fonts/Helvetica.ttc`

**Linux:**
- `/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc`
- `/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf`
- `/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf`

### Централизованные состояния FSM

Все состояния системы определены в одном файле для лучшей поддерживаемости:

```python
class StudyStates(StatesGroup):
    studying = State()
    confirming_word_knowledge = State()
    viewing_word_details = State()
    viewing_word_image = State()  # НОВОЕ: Просмотр изображения слова
    study_completed = State()
```

### Meta-состояния для обработки ошибок

Система автоматически переходит в специальные состояния при системных ошибках:

```python
class CommonStates(StatesGroup):
    handling_api_error = State()
    connection_lost = State()
    unknown_command = State()
```

## Отладка и мониторинг

### Проверка состояния системы

```bash
# Проверка конфигурации без запуска
python frontend/app/main_frontend.py --validate-only

# Запуск в режиме отладки
python frontend/app/main_frontend.py --debug

# Проверка статуса через бота
/status  # в Telegram боте
```

### Логирование

- **Структурированные логи** с уровнями важности
- **Автоматическое уведомление администраторов** о критических ошибках
- **Детальное логирование** процесса регистрации обработчиков
- **Контекстное логирование** для отладки проблем

## Лицензия

MIT

## Автор

Anton Mikhalev  
[@Anton_Mikhalev](https://t.me/Anton_Mikhalev)  
anton.v.mikhalev@gmail.com

## История изменений

### v1.2.0 (Текущая версия)
- ✅ **Команда `/show_big`** для показа крупных изображений

### v1.1.0
- ✅ Добавлены индивидуальные настройки подсказок
- ✅ Внедрены meta-состояния для обработки ошибок
- ✅ Централизованы состояния FSM
- ✅ Устранено дублирование кода в обработчиках
- ✅ Улучшена архитектура роутеров
- ✅ Добавлена система автоматического восстановления
- ✅ Оптимизирована обработка ошибок middleware

### v1.0.0
- Базовая функциональность изучения слов
- Система интервального повторения
- Административный интерфейс
- Поддержка множества языков

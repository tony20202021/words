# Language Learning Bot

Language Learning Bot - это продвинутый Telegram-бот для эффективного изучения иностранных языков с использованием системы интервального повторения, персонализированных подсказок и современных технологий обучения.

## 🌟 Возможности

- 📚 **Изучение слов** с системой интервального повторения
- 🎯 **Индивидуальные настройки** процесса обучения для каждого языка
- 💡 **Персонализированные подсказки** с индивидуальным управлением типами
- 🎤 **Голосовые подсказки** с поддержкой распознавания речи
- 🖼️ **Генерация крупных изображений слов** с Unicode поддержкой для всех языков
- 🤖 **AI генерация изображений** с ControlNet Union для визуального изучения
- 📥 **Экспорт словарей** в форматах Excel, CSV и JSON
- 📤 **Рассылка уведомлений** администраторами с учетом настроек пользователей
- 📊 **Детальное отслеживание прогресса** изучения
- 🌐 **Поддержка множества языков** включая нелатинские алфавиты
- 👨‍💼 **Административный интерфейс** с возможностью редактирования прямо из режима изучения

## 🏗️ Архитектура

Проект построен на современной модульной архитектуре с разделением на независимые сервисы:

- **Frontend**: Telegram-бот на Python с aiogram 3.x
- **Backend**: REST API на FastAPI с MongoDB
- **Writing Service**: Микросервис генерации картинок с AI (порт 8600)
- **Common**: Общие утилиты и компоненты

## 🚀 Быстрый старт

### Требования

- Python 3.8+
- MongoDB 5.0+
- Telegram Bot API ключ
- Pillow (для генерации изображений)
- FFmpeg (для обработки голоса, опционально)
- CUDA-совместимая GPU (для AI генерации)

### Установка и запуск

1. **Клонирование репозитория:**
   ```bash
   git clone https://github.com/username/language-learning-bot.git
   cd language-learning-bot
   ```

2. **Настройка окружения:**
   ```bash
   conda env create -f environment.yml
   conda activate language-learning-bot
   ```

3. **Конфигурация:**
   ```bash
   cp .env.example .env
   # Отредактируйте .env и добавьте ваш TELEGRAM_BOT_TOKEN
   ```

4. **Запуск сервисов:**
   ```bash
   ./start_1_db.sh          # Запуск MongoDB
   ./start_2_backend.sh     # Запуск бэкенда
   ./start_4_writing_service.sh # Запуск AI сервиса генерации изображений
   ./start_3_frontend.sh    # Запуск фронтенда (Telegram-бота)
   ```

5. **Начните использование:**
   - Откройте бота в Telegram
   - Отправьте `/start` для начала работы
   - Выберите язык командой `/language`
   - Начните изучение командой `/study`

## 📋 Основные команды

### 👤 Пользовательские команды:
- `/start` - Начать работу с ботом
- `/language` - Выбрать язык для изучения
- `/study` - Начать изучение слов
- `/settings` - Настройки процесса обучения и подсказок
- `/stats` - Показать статистику изучения
- `/show_big` - Показать крупное изображение текущего слова
- `/help` - Получить справку по работе с ботом

### 👨‍💼 Административные команды:
- `/admin` - Вход в административную панель
- `/managelang` - Управление языками
- `/upload` - Загрузка файлов со словами
- `/export` - **НОВОЕ:** Экспорт слов в Excel/CSV/JSON
- `/users` - Управление пользователями
- `/bot_stats` - Административная статистика

## 🧪 Тестирование

Проект имеет обширное тестовое покрытие:

```bash
# Запуск всех тестов
./run_tests.sh

# Запуск тестов с отчетом о покрытии
./run_tests.sh --coverage

# Запуск тестов конкретного модуля
python -m pytest frontend/tests/test_handlers/test_admin/
```

## 📖 Документация

Подробная документация доступна в директории `docs/`:

### 📋 Для пользователей:
- [🚀 Руководство по запуску](docs/running/running_guide.md)
- [🎮 Команды и функции бота](docs/functionality/bot_commands.md)
- [📚 Система изучения слов](docs/functionality/learning_system.md)
- [👨‍💼 Инструменты администрирования](docs/functionality/admin_tools.md)

### 🔧 Для разработчиков:
- [🏗️ Архитектура системы](docs/architecture.md)
- [📁 Структура каталогов](docs/development/directory_structure.md)
- [🧪 Разработка и тестирование](docs/development/testing_guide.md)
- [🔌 API-интерфейс](docs/api/api_reference.md)

## 🆕 История изменений

### **v1.7.0 (текущая версия):**
- 📤 **Рассылка уведомлений** администраторами всем пользователям
- ⚙️ **Настройки уведомлений** для пользователей (включить/отключить получение сообщений)
- 📊 **Обновляемый прогресс** отправки с детальной статистикой
- 🛡️ **Автоматическое исключение** администратора из рассылки
- 🔄 **Фильтрация получателей** по настройкам уведомлений
- ⏱️ **Задержки между отправками** для соблюдения лимитов Telegram
- 📝 **Подробное логирование** всех операций рассылки

### **v1.6.0:**
- 📥 **Экспорт словарей** в форматах Excel, CSV и JSON с фильтрацией по диапазону
- 🌐 **Unicode поддержка** для экспорта файлов с китайскими, арабскими и другими символами
- 🧹 **Очистка данных** при экспорте - автоматическое удаление переносов строк и лишних пробелов
- 🔧 **Улучшенная обработка ошибок** при генерации файлов экспорта

### **v1.5.0:**
- 🤖 **ControlNet Union интеграция** - единая модель для всех типов conditioning
- ⚡ **Оптимизация производительности** - уменьшение размера моделей с ~10GB до ~2.5GB
- 💾 **Экономия ресурсов** - снижение потребления VRAM до 40%
- 🎯 **Улучшенная fusion conditioning** - автоматическое объединение conditioning типов

### **v1.4.2:**
- 🖼️ **Система генерации изображений слов** с Unicode поддержкой
- 👨‍💼 **Админ-редактирование из изучения** без потери контекста
- 🎤 **Голосовые подсказки** с автоматическим распознаванием речи
- 📦 **Batch-загрузка слов** для оптимальной производительности

### **v1.3.0:**
- 💡 **Индивидуальные настройки подсказок** для каждого типа отдельно
- 🛡️ **Meta-состояния** для надежной обработки ошибок системы
- 🎯 **Централизованные состояния FSM** для лучшей организации кода

### **v1.0.0:**
- Базовая функциональность изучения слов
- Система интервального повторения
- Административный интерфейс
- Поддержка множества языков

## 📥 Экспорт словарей

### Поддерживаемые форматы:
- **📊 Excel (.xlsx)** - для просмотра и редактирования в Excel/LibreOffice
- **📄 CSV (.csv)** - универсальный формат для импорта в другие системы
- **🔧 JSON (.json)** - структурированные данные для программной обработки

### Возможности экспорта:
- **Полные словари** - экспорт всех слов языка
- **Фильтрация по диапазону** - экспорт слов с определенными номерами (например, 1-1000)
- **Unicode поддержка** - корректная обработка китайских, арабских и других символов
- **Автоматическая очистка** - удаление переносов строк и лишних пробелов
- **Метаинформация** - данные о языке, дате экспорта и параметрах в JSON

### Применение:
- Резервное копирование словарей
- Перенос данных между системами
- Анализ и обработка содержимого
- Подготовка материалов для печати
- Интеграция с внешними инструментами

## 📤 Рассылка уведомлений

### Основные возможности:
- **Массовая отправка** сообщений всем пользователям
- **Фильтрация получателей** по настройкам уведомлений
- **Автоматическое исключение** администратора-отправителя
- **Обновляемый прогресс** отправки в реальном времени
- **Детальная статистика** успешных и неуспешных доставок

### Технические характеристики:
- **Задержка**: 0.1 секунды между отправками
- **Максимальный размер**: 4096 символов в сообщении
- **Поддержка форматирования**: жирный текст, курсив, код
- **Обработка ошибок**: автоматическая обработка сбоев доставки

### Настройки пользователей:
- **Управление уведомлениями** через `/settings`
- **По умолчанию включены** для всех новых пользователей
- **Индивидуальный контроль** для каждого пользователя

### Применение:
- **Системные уведомления** об обновлениях
- **Объявления** о новых функциях
- **Технические работы** и перерывы в обслуживании
- **Поздравления** с праздниками
- **Напоминания** об активности в обучении

## 🎨 AI Генерация изображений

### Основные возможности:
- **ControlNet Union** - единая модель для всех типов conditioning
- **Multi-ControlNet** - поддержка canny, depth, segmentation, scribble
- **Stable Diffusion XL** - высококачественная генерация изображений
- **Prompt Engineering** - автоматическое построение промптов
- **GPU оптимизация** - автоматическая настройка под доступные ресурсы

### Технические характеристики:
- **Модель**: `xinsir/controlnet-union-sdxl-1.0`
- **Разрешение**: до 2048x2048 пикселей
- **Языки**: универсальная поддержка всех языков мира
- **Производительность**: ~8-12 секунд на RTX 4090

## 📄 Лицензия

MIT License - подробности в файле [LICENSE](LICENSE)

## 👨‍💻 Автор

**Anton Mikhalev**  
📱 Telegram: [@Anton_Mikhalev](https://t.me/Anton_Mikhalev)  
📧 Email: anton.v.mikhalev@gmail.com

---

⭐ **Если проект оказался полезным, поставьте звездочку!** ⭐
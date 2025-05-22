Проект по добавлению транскрипции к иностранным словам
Этот проект предназначен для автоматического добавления транскрипций к иностранным словам из Excel-файла или JSON-файла и сохранения результатов в формате JSON. Проект поддерживает работу с разными языками, включая немецкий, французский, испанский, английский, итальянский, нидерландский, португальский, русский и другие, используя комбинацию локальных словарей и различных сервисов транскрипции.
Описание
Проект решает задачу обогащения словаря иностранных слов транскрипциями в формате Международного фонетического алфавита (IPA). На входе система принимает Excel-файл или JSON-файл со словами, обрабатывает каждое слово, находит его транскрипцию с помощью различных сервисов и сохраняет результаты в JSON-файл.
Основные функции:

Чтение слов из Excel-файла или JSON-файла
Автоматическое определение языка слова (если не указан явно)
Получение транскрипций из различных источников:

Локальные словари
Epitran (локальная библиотека)
G2P и G2P_EN (локальные библиотеки)
Phonemizer (локальная библиотека с espeak-ng бэкендом)
CharsiuG2P (локальная мультиязычная модель)
Wiktionary API (онлайн-сервис)
Google Translate API (онлайн-сервис, неофициальный)
Forvo API (онлайн-сервис, требует API ключ)
EasyPronunciation API (онлайн-сервис, требует API ключ)
IBM Watson API (онлайн-сервис, требует API ключ)
OpenAI API (онлайн-сервис, требует API ключ)


Сохранение результатов в JSON-файл
Кэширование найденных транскрипций в локальных словарях

Поддерживаемые языки:

Немецкий (de)
Французский (fr)
Испанский (es)
Английский (en)
Итальянский (it)
Нидерландский (nl)
Португальский (pt)
Русский (ru)
Польский (pl)
Чешский (cs)
И другие (в зависимости от используемых сервисов)

Установка
Требования

Python 3.8 или новее
pip или conda
Доступ в интернет (для загрузки зависимостей и использования онлайн-сервисов)

# Установка зависимостей
pip install -r requirements.txt

# Создание необходимых директорий
mkdir -p data/dictionaries logs output
Использование
Базовое использование
Используйте bash-скрипт для простого запуска:
bash./scripts/transcribe.sh input.xlsx
Скрипт автоматически создаст виртуальное окружение, установит необходимые зависимости, загрузит локальные словари (если они отсутствуют) и запустит процесс добавления транскрипций.
Расширенное использование
Для более тонкой настройки можно использовать Python-скрипт напрямую:
bashpython src/transcription_script.py input.xlsx --output-file output.json --services dictionary epitran g2p
Параметры командной строки

input_file - путь к входному Excel или JSON файлу (обязательный параметр)
--output-file - путь к выходному JSON-файлу (по умолчанию равен входному файлу с заменой расширения)
--start-index - начальный индекс для обработки Excel-файла (по умолчанию: 0)
--end-index - конечный индекс для обработки Excel-файла (по умолчанию: до конца файла)
--lang-field - имя поля для кода языка (по умолчанию "language")
--word-field - имя поля со словом (по умолчанию "word")
--transcription-field - имя поля для транскрипции (по умолчанию "transcription")
--dict-dir - путь к директории со словарями (по умолчанию "data/dictionaries")
--language - код языка для всех слов (de, fr, es, en, ...)

API ключи:

--forvo-key - API ключ для Forvo
--easypronunciation-key - API ключ для EasyPronunciation
--ibm-watson-key - API ключ для IBM Watson
--openai-key - API ключ для OpenAI

Выбор сервисов:

--services - список сервисов для использования, разделенных пробелом: dictionary epitran forvo google wiktionary g2p phonemize easypronunciation ibm_watson charsiu openai all

Отдельные флаги для сервисов (будут проигнорированы, если указан --services):

--use-epitran - использовать Epitran
--use-wiktionary - использовать Wiktionary API
--use-forvo - использовать Forvo API
--use-google - использовать Google Translate API
--use-g2p - использовать G2P библиотеку
--use-phonemize - использовать Phonemizer
--use-easypronunciation - использовать EasyPronunciation API
--use-ibm-watson - использовать IBM Watson API
--use-charsiu - использовать CharsiuG2P
--use-openai - использовать OpenAI API

Прочие параметры:

--verbose, -v - подробный вывод
--help, -h - показать справку

Примеры
bash# Обработка Excel-файла с французскими словами
./scripts/transcribe.sh words.xlsx -l fr

# Использование только локальных сервисов
./scripts/transcribe.sh words.xlsx --services dictionary epitran g2p phonemize

# Использование онлайн-сервисов с API ключами
./scripts/transcribe.sh words.xlsx --forvo-key YOUR_FORVO_KEY --openai-key YOUR_OPENAI_KEY

# Обработка только определенных строк в Excel-файле
./scripts/transcribe.sh words.xlsx --start-index 100 --end-index 200

# Сохранение результатов в указанный файл
./scripts/transcribe.sh words.xlsx --output-file results.json
Обработка Excel-файлов
Скрипт поддерживает работу с Excel-файлами в форматах .xls и .xlsx. Основной алгоритм:

Чтение Excel-файла с помощью pandas
Извлечение слов из указанной колонки
Определение языка для каждого слова (если не указан)
Поиск транскрипции в локальном словаре или через сервисы
Сохранение результатов в JSON-файл

Пример структуры Excel-файла
Ожидается, что Excel-файл содержит таблицу со следующими колонками:

Колонка с номерами (индекс 0)
Колонка со словами (индекс 1)

Формат выходных данных
Результаты сохраняются в JSON-файл следующей структуры:
json{
    "1": {
        "word": "Schön",
        "transcription": "/ʃøːn/",
        "language": "de",
        "frequency": 1
    },
    "2": {
        "word": "bonjour",
        "transcription": "/bɔ̃ʒuʁ/",
        "language": "fr",
        "frequency": 2
    },
    "3": {
        "word": "gracias",
        "transcription": "/ˈgɾa.θjas/",
        "language": "es",
        "frequency": 3
    },
    "4": {
        "word": "hello",
        "transcription": "/həˈloʊ/",
        "language": "en",
        "frequency": 4
    }
}
Модульная структура
Проект имеет модульную структуру, позволяющую легко добавлять новые сервисы транскрипции:

src/services/base.py - базовый класс для всех сервисов транскрипции
src/services/dictionary_service.py - сервис на основе локальных словарей
src/services/epitran_service.py - сервис на основе библиотеки Epitran
src/services/g2p_service.py - сервис на основе библиотеки G2P
src/services/phonemize_service.py - сервис на основе библиотеки Phonemizer
src/services/wiktionary_service.py - сервис на основе Wiktionary API
src/services/google_service.py - сервис на основе Google Translate API
src/services/forvo_service.py - сервис на основе Forvo API
src/services/easypronunciation_service.py - сервис на основе EasyPronunciation API
src/services/ibm_watson_service.py - сервис на основе IBM Watson API
src/services/charsiu_g2p_service.py - сервис на основе CharsiuG2P
src/services/openai_service.py - сервис на основе OpenAI API

Все эти сервисы управляются через класс TranscriptionManager, который пытается получить транскрипцию, используя сервисы по порядку до первого успешного результата.
Поиск и устранение неисправностей
Проблема: Транскрипция не найдена для некоторых слов
Решение:

Проверьте наличие установленных зависимостей для локальных сервисов
Убедитесь, что у вас есть доступ в интернет для использования онлайн-сервисов
Проверьте правильность API ключей
Попробуйте использовать разные сервисы транскрипции с помощью параметра --services

Проблема: Ошибки при чтении Excel-файла
Решение:

Убедитесь, что Excel-файл имеет ожидаемую структуру
Проверьте, что у вас установлены необходимые зависимости для работы с Excel (openpyxl для .xlsx, xlrd для .xls)
Проверьте кодировку файла

Проблема: Неправильное определение языка
Решение:

Укажите язык явно с помощью параметра --language
Добавьте код языка в поле 'language' для каждого слова в JSON-файле
Установите библиотеку langdetect для улучшенного определения языка: pip install langdetect

Лицензия
MIT
Авторы
Anton Mikhalev
@Anton_Mikhalev
anton.v.mikhalev@gmail.com

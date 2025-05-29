"""
Функции для настройки мок-объектов API клиента в Bot Test Framework.
"""

from unittest.mock import AsyncMock

def setup_api_mock_for_common_scenarios(api_client: AsyncMock):
    """
    Настраивает основные сценарии для API-клиента.
    
    Args:
        api_client: Mock объект API-клиента
    """
    # Мокаем ответ для get_user_by_telegram_id (новый пользователь)
    api_client.get_user_by_telegram_id.return_value = {
        "success": True,
        "status": 200,
        "result": [],  # Пустой список = пользователь не найден
        "error": None
    }
    
    # Мокаем ответ для create_user
    api_client.create_user.return_value = {
        "success": True,
        "status": 201,
        "result": {"id": "user123"},
        "error": None
    }
    
    # Мокаем ответ для get_languages
    api_client.get_languages.return_value = {
        "success": True,
        "status": 200,
        "result": [
            {"id": "eng", "name_ru": "Английский", "name_foreign": "English"},
            {"id": "fra", "name_ru": "Французский", "name_foreign": "Français"}
        ],
        "error": None
    }

    # Мок для get_language (вызывается из get_language_by_id)
    api_client.get_language.return_value = {
        "success": True,
        "status": 200,
        "result": {"id": "eng", "name_ru": "Английский", "name_foreign": "English"},
        "error": None
    }    
    
    # Мокаем ответ для get_user_progress
    api_client.get_user_progress.return_value = {
        "success": True,
        "status": 200,
        "result": {'user_id': 'user123', 'language_id': 'eng', 'language_name_ru': 'Английский', 'language_name_foreign': 'English', 'total_words': 1001, 'words_studied': 0, 'words_known': 0, 'words_skipped': 0, 'progress_percentage': 0.0, 'last_study_date': None}, 
        "error": None
    }
    
    # Мокаем ответ для get_word_count_by_language - добавляем это
    api_client.get_word_count_by_language.return_value = {
        "success": True,
        "status": 200,
        "result": {"count": 1000},
        "error": None
    }
    
    api_client.get_words_for_review.return_value = {
        "success": True,
        "status": 200,
        "result": [{'language_id': 'eng', 'word_foreign': '行业', 'translation': 'I.1. отрасль (производства), индустрия; промысел\nI.2. профессия, занятие, специальность; профессиональный\nII.1. поведение, манеры', 'transcription': 'hángyè, xíngyè', 'word_number': 1001, 'sound_file_path': None, 'id': '6818cd67a20b11075e1265e1', 'created_at': '2025-05-05T14:38:31.237000', 'updated_at': '2025-05-05T14:38:31.237000'}], 
        "error": None
    }

    api_client.get_words_by_language.return_value = {
        "success": True,
        "status": 200,
        "result": [{'language_id': 'eng', 'word_foreign': '行业', 'translation': 'I.1. отрасль (производства), индустрия; промысел\nI.2. профессия, занятие, специальность; профессиональный\nII.1. поведение, манеры', 'transcription': 'hángyè, xíngyè', 'word_number': 1001, 'sound_file_path': None, 'id': '6818cd67a20b11075e1265e1', 'created_at': '2025-05-05T14:38:31.237000', 'updated_at': '2025-05-05T14:38:31.237000'}], 
        "error": None
    }

    # Добавляем мок для get_study_words
    api_client.get_study_words.return_value = {
        "success": True,
        "status": 200,
        "result": [
            {
                "id": "word123",
                "language_id": "eng",
                "word_foreign": "house",
                "translation": "дом",
                "transcription": "haʊs",
                "word_number": 10
            },
            {
                "id": "word124",
                "language_id": "eng",
                "word_foreign": "car",
                "translation": "машина",
                "transcription": "kɑr",
                "word_number": 11
            }
        ],
        "error": None
    }
    
    # Мокируем данные для тестирования подсказок
    api_client.get_user_word_data.return_value = {
        "success": True,
        "status": 200,
        "result": {
            "word_id": "word123",
            "score": 0,
            "hint_phoneticsound": None,
            "hint_phoneticassociation": None,
            "hint_meaning": None,
            "hint_writing": None,
            "check_interval": 0,
            "next_check_date": None,
            "is_skipped": False
        },
        "error": None
    }
    
    # Мокируем обновление данных слова
    api_client.update_user_word_data.return_value = {
        "success": True,
        "status": 200,
        "result": {
            "word_id": "word123",
            "score": 1,
            "check_interval": 1,
            "next_check_date": "2025-05-12",
            "is_skipped": False
        },
        "error": None
    }

    print("API клиент настроен для типовых сценариев тестирования")

def setup_api_mock_for_study_testing(api_client: AsyncMock):
    """
    Настраивает мок API клиента специально для тестирования функциональности изучения слов.
    """
    # Базовая настройка
    setup_api_mock_for_common_scenarios(api_client)
    
    # Мокируем динамическое изменение возвращаемого значения update_user_word_data
    async def dynamic_update_word_data(user_id, word_id, data):
        # В зависимости от переданных данных возвращаем разный результат
        if "score" in data and data["score"] == 1:
            # Если устанавливается оценка 1, рассчитываем интервал
            check_interval = 1
            if "check_interval" in data:
                # Если передан интервал, используем его
                check_interval = data["check_interval"]
            
            return {
                "success": True,
                "status": 200,
                "result": {
                    "word_id": word_id,
                    "score": 1,
                    "check_interval": check_interval,
                    "next_check_date": "2025-05-12T00:00:00.000Z",  # Заглушка
                    "is_skipped": False
                },
                "error": None
            }
        elif "hint_phoneticsound" in data:
            # Если создается фонетическая подсказка, возвращаем данные с подсказкой
            return {
                "success": True,
                "status": 200,
                "result": {
                    "word_id": word_id,
                    "score": 0,  # При создании подсказки оценка 0
                    "check_interval": 0,
                    "next_check_date": None,
                    "hint_phoneticsound": data["hint_phoneticsound"],
                    "is_skipped": False
                },
                "error": None
            }
        elif "hint_phoneticassociation" in data:
            # Если создается подсказка ассоциации, возвращаем данные с подсказкой
            return {
                "success": True,
                "status": 200,
                "result": {
                    "word_id": word_id,
                    "score": 0,  # При создании подсказки оценка 0
                    "check_interval": 0,
                    "next_check_date": None,
                    "hint_phoneticassociation": data["hint_phoneticassociation"],
                    "is_skipped": False
                },
                "error": None
            }
        elif "hint_meaning" in data:
            # Если создается подсказка значения, возвращаем данные с подсказкой
            return {
                "success": True,
                "status": 200,
                "result": {
                    "word_id": word_id,
                    "score": 0,  # При создании подсказки оценка 0
                    "check_interval": 0,
                    "next_check_date": None,
                    "hint_meaning": data["hint_meaning"],
                    "is_skipped": False
                },
                "error": None
            }
        elif "hint_writing" in data:
            # Если создается подсказка по написанию, возвращаем данные с подсказкой
            return {
                "success": True,
                "status": 200,
                "result": {
                    "word_id": word_id,
                    "score": 0,  # При создании подсказки оценка 0
                    "check_interval": 0,
                    "next_check_date": None,
                    "hint_writing": data["hint_writing"],
                    "is_skipped": False
                },
                "error": None
            }
        elif "is_skipped" in data:
            # Если меняется статус пропуска
            return {
                "success": True,
                "status": 200,
                "result": {
                    "word_id": word_id,
                    "score": 0,
                    "check_interval": 0,
                    "next_check_date": None,
                    "is_skipped": data["is_skipped"]
                },
                "error": None
            }
        
        # Базовый случай
        return {
            "success": True,
            "status": 200,
            "result": {
                "word_id": word_id,
                "score": 0,
                "check_interval": 0,
                "next_check_date": None,
                "is_skipped": False
            },
            "error": None
        }
    
    # Применяем динамический мок
    api_client.update_user_word_data.side_effect = dynamic_update_word_data
    
    print("API клиент настроен для тестирования изучения слов")


def setup_api_mock_for_error_testing(api_client: AsyncMock):
    """
    Настраивает мок API клиента для тестирования обработки ошибок.
    """
    # Метод get_user_by_telegram_id возвращает ошибку
    api_client.get_user_by_telegram_id.return_value = {
        "success": False,
        "status": 500,
        "result": None,
        "error": "Ошибка соединения с базой данных"
    }
    
    # Метод get_languages возвращает ошибку
    api_client.get_languages.return_value = {
        "success": False,
        "status": 500,
        "result": None,
        "error": "Ошибка загрузки списка языков"
    }
    
    # Метод get_study_words возвращает ошибку
    api_client.get_study_words.return_value = {
        "success": False,
        "status": 500,
        "result": None,
        "error": "Ошибка получения слов для изучения"
    }
    
    # Метод get_user_word_data возвращает ошибку
    api_client.get_user_word_data.return_value = {
        "success": False,
        "status": 404,
        "result": None,
        "error": "Данные слова не найдены"
    }
    
    # Метод update_user_word_data возвращает ошибку
    api_client.update_user_word_data.return_value = {
        "success": False,
        "status": 500,
        "result": None,
        "error": "Ошибка обновления данных слова"
    }
    
    print("API клиент настроен для тестирования обработки ошибок")
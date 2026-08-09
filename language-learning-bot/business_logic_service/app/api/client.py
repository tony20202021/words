"""
API client for interacting with the backend service.
This client is used by the frontend to communicate with the backend API,
not directly with the database.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from urllib.parse import quote

import aiohttp
from dotenv import load_dotenv

from app.logger import get_module_logger


# Загрузка переменных окружения
load_dotenv()

# Настройка логгера
logger = get_module_logger(__name__)

class APIClient:
    """
    Client for interacting with the backend API.
    """
    
    def __init__(self, base_url: str, api_prefix: str = "/api", timeout: int = 5, retry_count: int = 3):
        """
        Initialize API client.
        
        Args:
            base_url: Base URL of the backend API
            api_prefix: Prefix for API endpoints
            timeout: Request timeout in seconds
            retry_count: Number of retry attempts for failed requests
        """
        self.base_url = base_url
        self.api_prefix = api_prefix
        self.timeout = timeout
        self.retry_count = retry_count
        logger.info(f"Initialized API client with base URL: {self.base_url}{self.api_prefix}")

    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None, 
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make a request to the API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH)
            endpoint: API endpoint
            data: Request data
            params: Query parameters
            
        Returns:
            Dict with status and result fields: 
            {
                "success": bool,  # True if request was successful
                "status": int,    # HTTP status code (200, 404, 500, etc.) or 0 if connection failed
                "result": Any,    # Response data or None
                "error": str      # Error message if any
            }
        """
        url = f"{self.base_url}{self.api_prefix}{endpoint}"
        
        response_dict = {
            "success": False,
            "status": 0,
            "result": None,
            "error": None
        }
        
        # Преобразуем булевы значения в строки для корректной передачи параметров
        if params:
            processed_params = {}
            for key, value in params.items():
                if isinstance(value, bool):
                    processed_params[key] = str(value).lower()
                else:
                    processed_params[key] = value
            params = processed_params
        
        # Добавляем поддержку повторных попыток при ошибках
        for attempt in range(self.retry_count):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.request(
                        method=method,
                        url=url,
                        json=data,
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:
                        response_dict["status"] = response.status
                        
                        if response.status >= 400:
                            error_data = await response.json()
                            error_message = str(error_data)
                            logger.error(f"API error: {response.status} - {error_data}")
                            response_dict["error"] = error_message
                            
                            # Если ошибка 429 (слишком много запросов) или 5xx (ошибка сервера), пробуем ещё раз
                            if response.status == 429 or response.status >= 500:
                                if attempt < self.retry_count - 1:
                                    logger.warning(f"Retrying request (attempt {attempt+1}/{self.retry_count})...")
                                    continue
                            return response_dict
                        
                        # Проверяем, возвращает ли ответ JSON
                        if response.content_type == 'application/json':
                            response_dict["result"] = await response.json()
                        else:
                            response_dict["result"] = await response.text()
                        
                        response_dict["success"] = True
                        return response_dict
                
            except aiohttp.ClientError as e:
                error_message = f"API request failed: {e}"
                logger.error(error_message)
                response_dict["error"] = error_message
                
                if attempt < self.retry_count - 1:
                    logger.warning(f"Retrying request (attempt {attempt+1}/{self.retry_count})...")
                    continue
        
        # Если все попытки провалились
        logger.error(f"All {self.retry_count} attempts to make a request failed")
        return response_dict

    # Languages
    
    async def get_languages(self) -> Optional[Dict]:
        """Get all languages."""
        result = await self._make_request("GET", "/languages")
        return result
        
    async def get_language(self, language_id: str) -> Optional[Dict]:
        """Get language by ID."""
        return await self._make_request("GET", f"/languages/{language_id}")
    
    async def create_language(self, language_data: Dict) -> Optional[Dict]:
        """Create a new language."""
        return await self._make_request("POST", "/languages", data=language_data)
    
    async def update_language(self, language_id: str, language_data: Dict) -> Optional[Dict]:
        """Update language by ID."""
        return await self._make_request("PUT", f"/languages/{language_id}", data=language_data)
    
    async def delete_language(self, language_id: str) -> Dict[str, Any]:
        """Delete language by ID."""
        result = await self._make_request("DELETE", f"/languages/{language_id}")
        return result
    
    # Words
    
    async def get_words_by_language(self, language_id: str, skip: int = 0, limit: int = 100) -> Optional[Dict]:
        """Get words for a language with pagination."""
        params = {"skip": skip, "limit": limit}
        result = await self._make_request("GET", f"/languages/{language_id}/words", params=params)
        return result
    
    async def get_word(self, word_id: str) -> Optional[Dict]:
        """Get word by ID."""
        return await self._make_request("GET", f"/words/{word_id}")
    
    async def get_word_by_number(self, language_id: str, word_number: int) -> Optional[Dict]:
        """Get word by language ID and word number."""
        params = {"word_number": word_number}
        result = await self._make_request("GET", f"/languages/{language_id}/words", params=params)
        return result
    
    async def create_word(self, word_data: Dict) -> Optional[Dict]:
        """Create a new word."""
        return await self._make_request("POST", "/words", data=word_data)
    
    async def update_word(self, word_id: str, word_data: Dict) -> Optional[Dict]:
        """Update word by ID."""
        return await self._make_request("PUT", f"/words/{word_id}", data=word_data)
    
    async def delete_word(self, word_id: str) -> Dict[str, Any]:
        """Delete word by ID."""
        result = await self._make_request("DELETE", f"/words/{word_id}")
        return result

    async def upload_words_file(
        self, 
        language_id: str, 
        file_data: bytes, 
        file_name: str, 
        params: Optional[Dict] = None,
        timeout_multiplier: int = 3
    ) -> Dict[str, Any]:
        """
        Upload words file (Excel).
        
        Args:
            language_id: ID of the language
            file_data: Binary content of the file
            file_name: Name of the file
            params: Additional parameters for file processing (default: None)
                - column_word: Column index for foreign words
                - column_translation: Column index for translations
                - column_transcription: Column index for transcriptions
                - column_radicals: Column index for radicals
                - column_references: Column index for references
                - column_tones: Column index for tones
                - column_sounds: Column index for sounds
                - column_number: Column index for word numbers
                - start_row: Index of the first row to process (0 if no headers, 1 if headers)
                - clear_existing: Whether to clear existing words before importing (bool)
            timeout_multiplier: Multiplier for the timeout (default: 3)
                            Operations with files usually take longer than regular API calls
                            
        Returns:
            Dict with status and result fields: 
            {
                "success": bool,  # True if request was successful
                "status": int,    # HTTP status code (200, 404, 500, etc.) or 0 if connection failed
                "result": Any,    # Response data or None
                "error": str      # Error message if any
            }
        """
        url = f"{self.base_url}{self.api_prefix}/languages/{language_id}/upload"
        
        response_dict = {
            "success": False,
            "status": 0,
            "result": None,
            "error": None
        }
        
        # Добавляем поддержку повторных попыток при ошибках
        for attempt in range(self.retry_count):
            try:
                form_data = aiohttp.FormData()
                form_data.add_field('file', 
                            file_data,
                            filename=file_name,
                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                
                # Добавляем параметры колонок в форму, если они предоставлены
                logger.info(f"Params: {params}")
                if params:
                    processed_params = {}
                    for key, value in params.items():
                        # Преобразуем булевы значения в строки
                        if isinstance(value, bool):
                            processed_params[key] = str(value).lower()
                        else:
                            processed_params[key] = value
                            
                    for key, value in processed_params.items():
                        if value is not None:  # Добавляем только непустые значения
                            form_data.add_field(key, str(value))
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url,
                        data=form_data,
                        timeout=aiohttp.ClientTimeout(total=self.timeout * timeout_multiplier)
                    ) as response:
                        response_dict["status"] = response.status
                        
                        if response.status >= 400:
                            error_data = await response.json()
                            error_message = str(error_data)
                            logger.error(f"File upload error: {response.status} - {error_data}")
                            response_dict["error"] = error_message
                            
                            # Если ошибка 429 (слишком много запросов) или 5xx (ошибка сервера), пробуем ещё раз
                            if response.status == 429 or response.status >= 500:
                                if attempt < self.retry_count - 1:
                                    logger.warning(f"Retrying file upload (attempt {attempt+1}/{self.retry_count})...")
                                    continue
                            return response_dict
                        
                        # Проверяем, возвращает ли ответ JSON
                        if response.content_type == 'application/json':
                            response_dict["result"] = await response.json()
                        else:
                            response_dict["result"] = await response.text()
                        
                        response_dict["success"] = True
                        return response_dict
                
            except aiohttp.ClientError as e:
                error_message = f"File upload failed: {e}"
                logger.error(error_message)
                response_dict["error"] = error_message
                
                if attempt < self.retry_count - 1:
                    logger.warning(f"Retrying file upload (attempt {attempt+1}/{self.retry_count})...")
                    continue
        
        # Если все попытки провалились
        logger.error(f"All {self.retry_count} attempts to upload file failed")
        return response_dict

    # Users
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict]:
        """Get user by Telegram ID."""
        params = {"telegram_id": telegram_id}
        return await self._make_request("GET", "/users", params=params)
    
    async def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user by MongoDB ObjectId."""
        return await self._make_request("GET", f"/users/{user_id}")

    async def create_user(self, user_data: Dict) -> Optional[Dict]:
        """Create a new user."""
        return await self._make_request("POST", "/users", data=user_data)
    
    async def update_user(self, user_id: str, user_data: Dict) -> Optional[Dict]:
        """Update user by ID."""
        return await self._make_request("PUT", f"/users/{user_id}", data=user_data)
    
    # User Progress
        
    async def get_user_progress(self, user_id: str, language_id: Optional[str] = None) -> Optional[Dict]:
        """
        Get user progress, optionally filtered by language.
        
        Args:
            user_id: The user ID
            language_id: Optional language ID filter
            
        Returns:
            Dict with user progress information
        """
        if language_id:
            # Используем правильный маршрут для конкретного языка
            return await self._make_request("GET", f"/users/{user_id}/languages/{language_id}/progress")
        else:
            # Для получения всех прогрессов используем другой маршрут
            return await self._make_request("GET", f"/users/{user_id}/progress")
    
    # User Word Data
    
    async def get_user_word_data(self, user_id: str, word_id: str) -> Optional[Dict]:
        """
        Get user data for a specific word.
        
        Args:
            user_id: The user ID
            word_id: The word ID
            
        Returns:
            Dict with user word data, including hints and learning progress
        """
        return await self._make_request("GET", f"/users/{user_id}/word_data/{word_id}")
    
    async def create_user_word_data(self, user_id: str, word_data: Dict) -> Optional[Dict]:
        """
        Create user word data.
        
        Args:
            user_id: The user ID
            word_data: The word data to create
            
        Returns:
            Dict with created user word data
        """
        return await self._make_request("POST", f"/users/{user_id}/word_data", data=word_data)
    
    async def update_user_word_data(self, user_id: str, word_id: str, word_data: Dict) -> Optional[Dict]:
        """
        Update user word data.
        
        Args:
            user_id: The user ID
            word_id: The word ID
            word_data: The word data to update
            
        Returns:
            Dict with updated user word data
        """
        return await self._make_request("PUT", f"/users/{user_id}/word_data/{word_id}", data=word_data)
        # TODO проверить бэкенд - не сохраняется дата None
    
    async def get_words_by_numbers_for_quiz(
        self, language_id: str, word_numbers: List[int]
    ) -> Optional[Dict]:
        """Batch-fetch words by a list of word numbers for quiz distractor generation."""
        if not word_numbers:
            return {"success": True, "result": []}
        numbers_str = ",".join(str(n) for n in word_numbers)
        return await self._make_request(
            "GET", f"/languages/{language_id}/words/by-numbers",
            params={"numbers": numbers_str}
        )

    async def get_words_by_unit_count(
        self, language_id: str, modality: str, unit_count: int, max_word_number: int, limit: int = 30
    ) -> Optional[Dict]:
        """Fetch words by unit count for targeted quiz distractor generation."""
        return await self._make_request(
            "GET", f"/languages/{language_id}/words/by-unit-count",
            params={"modality": modality, "unit_count": unit_count, "max_word_number": max_word_number, "limit": limit}
        )

    # Study words

    async def get_study_words(self, user_id: str, language_id: str, params: Dict, limit: int = 100) -> Optional[Dict]:
        """
        Get words for study with various filters.
        ОБНОВЛЕНО: Поддержка параметра skip для пагинации.
        """
        # Добавляем limit к существующим параметрам
        if params is None:
            params = {}
        
        # Базовый API ожидает строки для булевых значений
        processed_params = {}
        for key, value in params.items():
            if key in ["skip_marked", "use_check_date"] and isinstance(value, bool):
                processed_params[key] = str(value).lower()
            else:
                processed_params[key] = value
                
        processed_params["limit"] = limit
        
        # НОВОЕ: Поддержка skip для пагинации
        if "skip" in params:
            processed_params["skip"] = params["skip"]
        
        # Логируем финальные параметры запроса
        logger.info(f"Making request to get_study_words for user_id={user_id}, language_id={language_id}, "
                    f"processed_params={processed_params}")
        
        result = await self._make_request(
            "GET", 
            f"/users/{user_id}/languages/{language_id}/study", 
            params=processed_params
        )
        
        # Логируем результат запроса
        if not result["success"]:
            logger.error(f"get_study_words failed: status={result['status']}, error={result['error']}")
        else:
            logger.info(f"get_study_words success: got {len(result['result']) if result['result'] else 0} words")
        
        return result

    async def get_word_count_by_language(self, language_id: str) -> Dict[str, Any]:
        """
        Get the count of words for a specific language.
        
        Args:
            language_id: ID of the language
            
        Returns:
            Dictionary with count information:
            {
                "success": bool,
                "status": int,
                "result": {
                    "count": int
                },
                "error": str or None
            }
        """
        return await self._make_request("GET", f"/languages/{language_id}/count")
        
    async def get_users_count(self) -> Dict[str, Any]:
        """
        Get the total count of users in the system.
        
        Returns:
            Dict with standard response format containing user count in result.
        """
        return await self._make_request("GET", "/users/count")
        
    async def get_language_active_users(self, language_id: str) -> Dict[str, Any]:
        """
        Get the count of active users for a specific language.
        
        Args:
            language_id: ID of the language
            
        Returns:
            Dict with standard response format containing active users count in result.
        """
        return await self._make_request("GET", f"/languages/{language_id}/users/count")
        
    async def get_users(self, skip: int = 0, limit: int = 100) -> Dict[str, Any]:
        """
        Get list of users with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            Dict with standard response format containing users list in result.
        """
        params = {"skip": skip, "limit": limit}
        return await self._make_request("GET", "/users", params=params)

    # User Language Settings - Базовые методы

    async def get_user_language_settings(self, user_id: str, language_id: str) -> Dict[str, Any]:
        """
        Get settings for a specific user and language.
        
        Args:
            user_id: User ID
            language_id: Language ID
            
        Returns:
            API response with settings in result field
        """
        endpoint = f"/users/{user_id}/languages/{language_id}/settings"
        return await self._make_request("GET", endpoint)

    async def update_user_language_settings(self, user_id: str, language_id: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update settings for a specific user and language.
        
        Args:
            user_id: User ID
            language_id: Language ID
            settings: Settings data to update
            
        Returns:
            API response with updated settings in result field
        """
        endpoint = f"/users/{user_id}/languages/{language_id}/settings"
        logger.info(f"Updating user language settings: {settings}")
        return await self._make_request("PUT", endpoint, data=settings)

    # НОВЫЕ МЕТОДЫ ДЛЯ РАБОТЫ С ИНДИВИДУАЛЬНЫМИ НАСТРОЙКАМИ ПОДСКАЗОК

    async def get_hint_settings(self, user_id: str, language_id: str) -> Dict[str, Any]:
        """
        Get hint settings for a specific user and language.
        
        Args:
            user_id: User ID
            language_id: Language ID
            
        Returns:
            API response with hint settings in result field
        """
        endpoint = f"/users/{user_id}/languages/{language_id}/settings/hints"
        
        logger.info(f"Getting hint settings for user_id={user_id}, language_id={language_id}")
        
        return await self._make_request("GET", endpoint)

    # Export methods

    async def export_words_by_language(
        self,
        language_id: str,
        format: str = "xlsx",
        start_word: Optional[int] = None,
        end_word: Optional[int] = None,
        timeout_multiplier: int = 5
    ) -> Dict[str, Any]:
        """
        Export words for a specific language in various formats.
        
        Args:
            language_id: ID of the language to export
            format: Export format - "xlsx" (default), "csv", or "json"
            start_word: Optional start word number (inclusive filtering)
            end_word: Optional end word number (inclusive filtering)
            timeout_multiplier: Multiplier for the timeout (default: 5)
                              Export operations can take longer than regular API calls
            
        Returns:
            Dict with status and result fields:
            {
                "success": bool,  # True if request was successful
                "status": int,    # HTTP status code (200, 404, 500, etc.) or 0 if connection failed
                "result": bytes,  # Binary file data for download/sending
                "error": str      # Error message if any
            }
        """
        url = f"{self.base_url}{self.api_prefix}/languages/{language_id}/export"
        
        response_dict = {
            "success": False,
            "status": 0,
            "result": None,
            "error": None
        }
        
        # Prepare query parameters
        params = {"format": format}
        if start_word is not None:
            params["start_word"] = start_word
        if end_word is not None:
            params["end_word"] = end_word
        
        logger.info(f"Exporting words for language_id={language_id}, format={format}, "
                   f"start_word={start_word}, end_word={end_word}")
        
        # Retry logic for export operations
        for attempt in range(self.retry_count):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url,
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=self.timeout * timeout_multiplier)
                    ) as response:
                        response_dict["status"] = response.status

                        if response.status >= 400:
                            # Try to get JSON error if possible
                            try:
                                error_data = await response.json()
                                error_message = error_data.get("error", f"HTTP {response.status}")
                            except Exception:
                                error_message = f"HTTP {response.status}: {response.reason}"
                            
                            logger.error(f"Export error: {response.status} - {error_message}")
                            response_dict["error"] = error_message
                            
                            # Retry on server errors or rate limits
                            if response.status == 429 or response.status >= 500:
                                if attempt < self.retry_count - 1:
                                    logger.warning(f"Retrying export (attempt {attempt+1}/{self.retry_count})...")
                                    continue
                            return response_dict
                        
                        # Read binary file data
                        file_data = await response.read()
                        response_dict["result"] = file_data
                        response_dict["success"] = True
                        
                        logger.info(f"Successfully exported {len(file_data)} bytes for language_id={language_id}")
                        return response_dict
                
            except aiohttp.ClientError as e:
                error_message = f"Export request failed: {e}"
                logger.error(error_message)
                response_dict["error"] = error_message
                
                if attempt < self.retry_count - 1:
                    logger.warning(f"Retrying export (attempt {attempt+1}/{self.retry_count})...")
                    continue
        
        # If all attempts failed
        logger.error(f"All {self.retry_count} attempts to export words failed")
        return response_dict
        
        
    async def get_daily_statistics(
        self, 
        user_id: str, 
        language_id: str, 
        date: datetime.date
    ) -> Dict[str, Any]:
        """
        Get daily statistics for a specific user, language, and date.
        
        Args:
            user_id: User ID
            language_id: Language ID
            date: Date for statistics
            
        Returns:
            API response with daily statistics in result field
        """
        endpoint = f"/users/{user_id}/languages/{language_id}/daily-stats/{date.isoformat()}"
        
        logger.info(f"Getting daily statistics for user_id={user_id}, language_id={language_id}, "
                   f"date={date}")
        
        return await self._make_request("GET", endpoint)


    async def update_daily_statistics(
        self,
        user_id: str,
        language_id: str,
        date: datetime.date,
        stats_update: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update daily statistics for a specific user, language, and date.
        
        Args:
            user_id: User ID
            language_id: Language ID
            date: Date for statistics
            stats_update: Statistics data to update
            
        Returns:
            API response with updated daily statistics
        """
        endpoint = f"/users/{user_id}/languages/{language_id}/daily-stats/{date.isoformat()}"
        
        logger.info(f"Updating daily statistics for user_id={user_id}, language_id={language_id}, "
                   f"date={date}, updates={stats_update}")
        
        return await self._make_request("PUT", endpoint, data=stats_update)        


    async def get_all_monthly_statistics(
        self,
        user_id: str,
        language_id: str,
        date: datetime.date
    ) -> Dict[str, Any]:
        """
        Get all monthly statistics aggregation for a user and language.
        
        Args:
            user_id: User ID
            language_id: Language ID
            date: Date for statistics
            
        Returns:
            API response with all monthly statistics
        """
        endpoint = f"/users/{user_id}/languages/{language_id}/all-monthly-stats/{date.isoformat()}"
        
        logger.info(f"Getting all monthly statistics for user_id={user_id}, language_id={language_id}, "
                   f"date={date}")
        
        return await self._make_request("GET", endpoint)


    async def get_monthly_statistics(
        self,
        user_id: str,
        language_id: str,
        date: datetime.date
    ) -> Dict[str, Any]:
        """
        Get monthly statistics aggregation for a user and language.
        
        Args:
            user_id: User ID
            language_id: Language ID
            date: Date for statistics
            
        Returns:
            API response with monthly statistics
        """
        endpoint = f"/users/{user_id}/languages/{language_id}/monthly-stats/{date.isoformat()}"
        
        logger.info(f"Getting monthly statistics for user_id={user_id}, language_id={language_id}, "
                   f"date={date}")
        
        return await self._make_request("GET", endpoint)


    async def update_daily_first_finish_statistics(
        self,
        user_id: str,
        language_id: str,
        date: datetime.date,
        stats_update: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update first finish statistics for a specific user and language.
        """
        endpoint = f"/users/{user_id}/languages/{language_id}/daily-first-finish-stats/{date.isoformat()}"
        return await self._make_request("PUT", endpoint, data=stats_update)

    async def update_daily_last_finish_statistics(
        self,
        user_id: str,
        language_id: str,
        date: datetime.date,
        stats_update: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update last-finish statistics (always overwrites — most recent session completion)."""
        endpoint = f"/users/{user_id}/languages/{language_id}/daily-last-finish-stats/{date.isoformat()}"
        return await self._make_request("PUT", endpoint, data=stats_update)

    async def get_all_monthly_first_finish_statistics(
        self,
        user_id: str,
        language_id: str,
        date: datetime.date
    ) -> Dict[str, Any]:
        """
        Get all monthly first finish statistics for a specific user and language.
        """
        endpoint = f"/users/{user_id}/languages/{language_id}/all-monthly-first-finish-stats/{date.isoformat()}"
        return await self._make_request("GET", endpoint)

    async def get_monthly_first_finish_statistics(
        self,
        user_id: str,
        language_id: str,
        date: datetime.date
    ) -> Dict[str, Any]:
        """
        Get monthly first finish statistics for a specific user and language.
        """
        endpoint = f"/users/{user_id}/languages/{language_id}/monthly-first-finish-stats/{date.isoformat()}"
        return await self._make_request("GET", endpoint)

    async def get_all_monthly_last_finish_statistics(
        self,
        user_id: str,
        language_id: str,
        date: datetime.date
    ) -> Dict[str, Any]:
        """Get all-time monthly last-finish statistics."""
        endpoint = f"/users/{user_id}/languages/{language_id}/all-monthly-last-finish-stats/{date.isoformat()}"
        return await self._make_request("GET", endpoint)

    async def get_monthly_last_finish_statistics(
        self,
        user_id: str,
        language_id: str,
        date: datetime.date
    ) -> Dict[str, Any]:
        """Get monthly last-finish statistics (recent 31 days)."""
        endpoint = f"/users/{user_id}/languages/{language_id}/monthly-last-finish-stats/{date.isoformat()}"
        return await self._make_request("GET", endpoint)

    async def get_sound_file(self, sound_name: str) -> Dict[str, Any]:
        """
        Get sound file by ID.
        Returns binary data (bytes) for the sound file.
        """
        # Quote the sound name and explicitly escape dots
        encoded_name = quote(sound_name, safe='').replace('.', '%2E')
        endpoint = f"/sounds/{encoded_name}"
        url = f"{self.base_url}{self.api_prefix}{endpoint}"
        
        response_dict = {
            "success": False,
            "status": 0,
            "result": None,
            "error": None
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=self.timeout)) as response:
                    response_dict["status"] = response.status
                    
                    if response.status >= 400:
                        try:
                            error_data = await response.json()
                        except Exception:
                            error_data = await response.text()
                        error_message = str(error_data)
                        logger.error(f"API error: {response.status} - {error_data}")
                        response_dict["error"] = error_message
                        return response_dict
                    
                    # Read binary data for sound file
                    response_dict["result"] = await response.read()
                    response_dict["success"] = True
                    return response_dict
                    
        except aiohttp.ClientError as e:
            error_message = f"API request failed: {e}"
            logger.error(error_message)
            response_dict["error"] = error_message
            return response_dict
        except Exception as e:
            error_message = f"Unexpected error: {e}"
            logger.error(error_message)
            response_dict["error"] = error_message
            return response_dict


# ── FastAPI dependency ────────────────────────────────────────────────────────

import os

_client: APIClient | None = None


def init_api_client(base_url: str) -> None:
    global _client
    _client = APIClient(base_url)


def get_api_client() -> APIClient:
    if _client is None:
        base_url = os.environ.get("BACKEND_URL", "http://localhost:8573")
        init_api_client(base_url)
    return _client
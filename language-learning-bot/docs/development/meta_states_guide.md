# Руководство по Meta-состояниям для разработчиков

## Содержание

1. [Архитектура Meta-состояний](#архитектура-meta-состояний)
2. [Реализация автоматических переходов](#реализация-автоматических-переходов)
3. [Обработчики Meta-состояний](#обработчики-meta-состояний)
4. [Система мониторинга и восстановления](#система-мониторинга-и-восстановления)
5. [Middleware интеграция](#middleware-интеграция)
6. [Тестирование Meta-состояний](#тестирование-meta-состояний)
7. [API для разработчиков](#api-для-разработчиков)

## Архитектура Meta-состояний

### Определение состояний

```python
# bot/states/centralized_states.py

class CommonStates(StatesGroup):
    """Meta-состояния для обработки системных ошибок"""
    
    handling_api_error = State()    # Ошибки API (4xx, 5xx)
    connection_lost = State()       # Потеря соединения с backend
    unknown_command = State()       # Неизвестные команды пользователя
```

### Модель данных для Meta-состояний

```python
# utils/state_models.py

@dataclass
class MetaStateData:
    """Данные для Meta-состояния"""
    
    error_type: str                    # Тип ошибки
    error_message: str                 # Сообщение об ошибке
    error_time: str                    # Время возникновения
    original_state: Optional[str]      # Исходное состояние
    recovery_attempts: int = 0         # Количество попыток восстановления
    user_data_backup: dict = None      # Резервная копия важных данных
    
    def to_state_data(self) -> dict:
        """Преобразование в данные для FSM состояния"""
        return asdict(self)
    
    @classmethod
    def from_state_data(cls, data: dict) -> 'MetaStateData':
        """Создание из данных FSM состояния"""
        return cls(**data)
```

## Реализация автоматических переходов

### Базовый класс для переходов

```python
# utils/error_utils.py

class MetaStateTransition:
    """Класс для управления переходами в Meta-состояния"""
    
    @staticmethod
    async def transition_to_api_error(
        message_obj: Union[Message, CallbackQuery],
        state: FSMContext,
        error_details: dict
    ) -> None:
        """Переход в состояние ошибки API"""
        
        # Сохранение текущего состояния
        current_state = await state.get_state()
        current_data = await state.get_data()
        
        # Создание Meta-состояния
        meta_data = MetaStateData(
            error_type="api_error",
            error_message=error_details.get("error", "Unknown API error"),
            error_time=str(datetime.now()),
            original_state=current_state,
            user_data_backup=_extract_important_data(current_data)
        )
        
        # Переход в Meta-состояние
        await state.set_state(CommonStates.handling_api_error)
        await state.update_data(**meta_data.to_state_data())
        
        # Уведомление пользователя
        await _send_error_notification(message_obj, "api_error", error_details)
        
        # Логирование
        logger.error(f"Transition to API error state: {error_details}")
    
    @staticmethod
    async def transition_to_connection_lost(
        message_obj: Union[Message, CallbackQuery],
        state: FSMContext
    ) -> None:
        """Переход в состояние потери соединения"""
        
        current_state = await state.get_state()
        current_data = await state.get_data()
        
        meta_data = MetaStateData(
            error_type="connection_lost",
            error_message="Connection to backend lost",
            error_time=str(datetime.now()),
            original_state=current_state,
            user_data_backup=_extract_important_data(current_data)
        )
        
        await state.set_state(CommonStates.connection_lost)
        await state.update_data(**meta_data.to_state_data())
        
        await _send_error_notification(message_obj, "connection_lost", {})
        
        logger.warning(f"Transition to connection lost state from {current_state}")

def _extract_important_data(state_data: dict) -> dict:
    """Извлечение важных данных пользователя"""
    
    important_keys = [
        "db_user_id",
        "current_language",
        "is_admin",
        "word_data",
        "study_settings"
    ]
    
    return {
        key: state_data.get(key)
        for key in important_keys
        if key in state_data and state_data[key] is not None
    }
```

### Интеграция с API клиентом

```python
# utils/error_utils.py

async def safe_api_call(
    api_func: Callable,
    message_obj: Union[Message, CallbackQuery],
    state: FSMContext,
    error_context: str = ""
) -> Tuple[bool, Any]:
    """
    Безопасный вызов API с автоматическим переходом в Meta-состояние
    
    Returns:
        Tuple[bool, Any]: (success, result)
    """
    
    try:
        result = await api_func()
        
        if isinstance(result, dict):
            if not result.get("success", False):
                # API вернул ошибку
                await MetaStateTransition.transition_to_api_error(
                    message_obj, state, result
                )
                return False, None
            
            return True, result.get("data")
        
        return True, result
        
    except aiohttp.ClientConnectorError:
        # Проблемы с соединением
        await MetaStateTransition.transition_to_connection_lost(
            message_obj, state
        )
        return False, None
        
    except asyncio.TimeoutError:
        # Таймаут
        error_details = {
            "error": f"Timeout in {error_context}",
            "status": 0
        }
        await MetaStateTransition.transition_to_api_error(
            message_obj, state, error_details
        )
        return False, None
        
    except Exception as e:
        # Неожиданная ошибка
        error_details = {
            "error": f"Unexpected error in {error_context}: {str(e)}",
            "status": 0
        }
        await MetaStateTransition.transition_to_api_error(
            message_obj, state, error_details
        )
        return False, None

# Пример использования в обработчике
async def cmd_study(message: Message, state: FSMContext, api_client):
    """Команда изучения с защитой от ошибок"""
    
    success, words = await safe_api_call(
        lambda: api_client.get_study_words(user_id, language_id, params),
        message,
        state,
        "получение слов для изучения"
    )
    
    if not success:
        # safe_api_call уже перевел в Meta-состояние
        return
    
    # Продолжаем обычную логику
    await show_study_words(message, words, state)
```

## Обработчики Meta-состояний

### Базовый класс обработчика

```python
# handlers/common_handlers.py

class MetaStateHandler:
    """Базовый класс для обработчиков Meta-состояний"""
    
    @staticmethod
    async def send_contextual_help(
        state: FSMContext,
        message_obj: Union[Message, CallbackQuery],
        additional_info: str = ""
    ) -> None:
        """Отправка контекстной помощи"""
        
        meta_data = MetaStateData.from_state_data(await state.get_data())
        
        help_text = []
        help_text.append(f"ℹ️ **Информация о проблеме:**")
        help_text.append(f"Тип: {meta_data.error_type}")
        help_text.append(f"Время: {meta_data.error_time}")
        
        if additional_info:
            help_text.append(f"\n{additional_info}")
        
        help_text.append(f"\n**Доступные команды:**")
        help_text.append(f"• `/retry` - попробовать еще раз")
        help_text.append(f"• `/start` - перезапустить бота")
        help_text.append(f"• `/status` - проверить состояние системы")
        
        await message_obj.answer("\n".join(help_text), parse_mode="Markdown")
```

### Обработчик ошибок API

```python
@common_router.message(StateFilter(CommonStates.handling_api_error))
async def handle_api_error_state(message: Message, state: FSMContext):
    """Обработка сообщений в состоянии ошибки API"""
    
    text = message.text.lower().strip() if message.text else ""
    meta_data = MetaStateData.from_state_data(await state.get_data())
    
    if text in ["/retry", "повторить"]:
        # Попытка восстановления
        success = await _attempt_recovery(message, state, meta_data)
        
        if success:
            await message.answer("✅ Соединение восстановлено! Можете продолжить работу.")
        else:
            meta_data.recovery_attempts += 1
            await state.update_data(**meta_data.to_state_data())
            
            if meta_data.recovery_attempts >= 3:
                await message.answer(
                    "❌ Не удается восстановить соединение.\n"
                    "Попробуйте позже или обратитесь к администратору."
                )
            else:
                await message.answer(
                    f"❌ Попытка восстановления не удалась ({meta_data.recovery_attempts}/3).\n"
                    "Попробуйте еще раз или используйте /start для перезапуска."
                )
    
    elif text in ["/start", "/help"]:
        # Выход из Meta-состояния с восстановлением данных
        await _restore_user_data(state, meta_data)
        await state.clear()
        await message.answer("Состояние сброшено. Можете продолжить работу.")
    
    else:
        # Контекстная помощь
        await MetaStateHandler.send_contextual_help(
            state, message,
            f"Ошибка API: {meta_data.error_message}"
        )

@common_router.callback_query(StateFilter(CommonStates.handling_api_error))
async def handle_api_error_callback(callback: CallbackQuery, state: FSMContext):
    """Обработка callback в состоянии ошибки API"""
    
    await callback.answer("❌ Сервис временно недоступен", show_alert=True)
    
    # Попытка автоматического восстановления
    meta_data = MetaStateData.from_state_data(await state.get_data())
    success = await _attempt_recovery(callback.message, state, meta_data)
    
    if success:
        await callback.message.answer("✅ Соединение восстановлено!")
```

### Обработчик потери соединения

```python
@common_router.message(StateFilter(CommonStates.connection_lost))
async def handle_connection_lost_state(message: Message, state: FSMContext):
    """Обработка сообщений в состоянии потери соединения"""
    
    text = message.text.lower().strip() if message.text else ""
    
    if text in ["/retry", "повторить"]:
        # Проверка восстановления соединения
        health = await check_system_health(message.bot)
        
        if health["api_connection"]:
            await _restore_from_connection_lost(message, state)
        else:
            await message.answer(
                "🔌 Соединение все еще недоступно.\n"
                "Попробуйте через несколько минут."
            )
    
    elif text in ["/start"]:
        # Принудительный выход из Meta-состояния
        await _restore_from_connection_lost(message, state)
    
    else:
        await MetaStateHandler.send_contextual_help(
            state, message,
            "🔌 Нет соединения с сервером. Проверьте подключение к интернету."
        )

async def _restore_from_connection_lost(message: Message, state: FSMContext):
    """Восстановление из состояния потери соединения"""
    
    meta_data = MetaStateData.from_state_data(await state.get_data())
    
    # Восстановление важных данных
    await _restore_user_data(state, meta_data)
    
    # Очистка Meta-состояния
    await state.clear()
    
    # Восстановление важных данных после очистки
    if meta_data.user_data_backup:
        await state.update_data(**meta_data.user_data_backup)
    
    await message.answer(
        "✅ Соединение восстановлено!\n"
        "Вы можете продолжить работу с того места, где остановились."
    )
```

## Система мониторинга и восстановления

### Health Check система

```python
# utils/health_check.py

async def check_system_health(bot: Bot) -> dict:
    """Проверка состояния системы"""
    
    health_status = {
        "bot_responsive": True,
        "api_connection": False,
        "database_accessible": False,
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        # Проверка API соединения
        api_client = get_api_client_from_bot(bot)
        health_response = await api_client._make_request("GET", "/health")
        health_status["api_connection"] = health_response.get("success", False)
        
        if health_status["api_connection"]:
            # Проверка доступности базы данных через API
            try:
                languages_response = await api_client.get_languages()
                health_status["database_accessible"] = languages_response.get("success", False)
            except Exception as e:
                logger.warning(f"Database check failed: {e}")
                health_status["database_accessible"] = False
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        health_status["api_connection"] = False
        health_status["database_accessible"] = False
    
    return health_status

async def _attempt_recovery(
    message: Message,
    state: FSMContext,
    meta_data: MetaStateData
) -> bool:
    """Попытка автоматического восстановления"""
    
    logger.info(f"Attempting recovery for error type: {meta_data.error_type}")
    
    # Проверка состояния системы
    health = await check_system_health(message.bot)
    
    if not health["api_connection"]:
        logger.warning("Recovery failed: API still unavailable")
        return False
    
    if not health["database_accessible"]:
        logger.warning("Recovery failed: Database still unavailable")
        return False
    
    # Восстановление пользовательских данных
    await _restore_user_data(state, meta_data)
    
    # Очистка Meta-состояния
    await state.clear()
    
    # Восстановление важных данных
    if meta_data.user_data_backup:
        await state.update_data(**meta_data.user_data_backup)
    
    logger.info("Recovery successful")
    return True

async def _restore_user_data(state: FSMContext, meta_data: MetaStateData):
    """Восстановление пользовательских данных"""
    
    if meta_data.original_state:
        try:
            # Попытка восстановить исходное состояние
            await state.set_state(meta_data.original_state)
            logger.info(f"Restored original state: {meta_data.original_state}")
        except Exception as e:
            logger.warning(f"Failed to restore original state: {e}")
    
    if meta_data.user_data_backup:
        # Восстановление важных данных пользователя
        await state.update_data(**meta_data.user_data_backup)
        logger.info("Restored user data backup")
```

## Middleware интеграция

### Enhanced AuthMiddleware

```python
# middleware/auth_middleware.py

class AuthMiddleware(BaseMiddleware):
    """Расширенное middleware с поддержкой Meta-состояний"""
    
    async def __call__(self, handler, event, data):
        try:
            # Проверка состояния системы перед обработкой
            if isinstance(event, (Message, CallbackQuery)):
                state = data.get("state")
                if state:
                    current_state = await state.get_state()
                    
                    # Пропускаем проверки для Meta-состояний
                    if current_state in [s.state for s in CommonStates.__all_states__]:
                        return await handler(event, data)
                    
                    # Проверка подключения к API
                    api_connectivity_ok = await self._ensure_api_connectivity(event, data, state)
                    if not api_connectivity_ok:
                        return  # Уже перешли в Meta-состояние
                    
                    # Проверка неизвестных команд
                    if isinstance(event, Message) and self._is_unknown_command(event):
                        await self._handle_unknown_command(event, state, event.text)
                        return
            
            return await handler(event, data)
            
        except Exception as e:
            logger.error(f"Error in AuthMiddleware: {e}")
            
            # Переход в Meta-состояние при неожиданной ошибке
            if isinstance(event, (Message, CallbackQuery)) and data.get("state"):
                await MetaStateTransition.transition_to_api_error(
                    event, data["state"],
                    {"error": f"Middleware error: {str(e)}", "status": 0}
                )
    
    async def _ensure_api_connectivity(self, event, data, state) -> bool:
        """Проверка подключения к API"""
        
        api_client = get_api_client_from_bot(data.get("bot"))
        if not api_client:
            await MetaStateTransition.transition_to_connection_lost(event, state)
            return False
        
        try:
            health_response = await api_client._make_request("GET", "/health")
            if not health_response.get("success"):
                await MetaStateTransition.transition_to_connection_lost(event, state)
                return False
        except Exception:
            await MetaStateTransition.transition_to_connection_lost(event, state)
            return False
        
        return True
    
    def _is_unknown_command(self, message: Message) -> bool:
        """Проверка на неизвестную команду"""
        
        if not message.text or not message.text.startswith("/"):
            return False
        
        known_commands = [
            "/start", "/help", "/language", "/study", "/settings", "/stats",
            "/hint", "/show_big", "/cancel", "/retry", "/status",
            "/admin", "/managelang", "/upload", "/bot_stats", "/users"
        ]
        
        command = message.text.split()[0].lower()
        return command not in known_commands
    
    async def _handle_unknown_command(self, message: Message, state: FSMContext, command: str):
        """Обработка неизвестной команды"""
        
        await MetaStateTransition.transition_to_unknown_command(message, state, command)
```

## Тестирование Meta-состояний

### Unit тесты

```python
# tests/test_utils/test_meta_states.py

import pytest
from unittest.mock import AsyncMock, Mock
from app.bot.states.centralized_states import CommonStates
from app.utils.error_utils import MetaStateTransition, safe_api_call

class TestMetaStateTransition:
    
    @pytest.mark.asyncio
    async def test_transition_to_api_error(self):
        """Тест перехода в состояние ошибки API"""
        
        # Arrange
        message = Mock()
        message.answer = AsyncMock()
        
        state = AsyncMock()
        state.get_state.return_value = "StudyStates:studying"
        state.get_data.return_value = {"db_user_id": "123", "current_language": "en"}
        state.set_state = AsyncMock()
        state.update_data = AsyncMock()
        
        error_details = {"error": "API Error", "status": 500}
        
        # Act
        await MetaStateTransition.transition_to_api_error(message, state, error_details)
        
        # Assert
        state.set_state.assert_called_once_with(CommonStates.handling_api_error)
        state.update_data.assert_called_once()
        message.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_safe_api_call_success(self):
        """Тест успешного вызова API"""
        
        # Arrange
        async def mock_api_func():
            return {"success": True, "data": "test_data"}
        
        message = Mock()
        state = AsyncMock()
        
        # Act
        success, result = await safe_api_call(mock_api_func, message, state)
        
        # Assert
        assert success is True
        assert result == "test_data"
    
    @pytest.mark.asyncio
    async def test_safe_api_call_failure(self):
        """Тест неудачного вызова API"""
        
        # Arrange
        async def mock_api_func():
            return {"success": False, "error": "API Error"}
        
        message = Mock()
        message.answer = AsyncMock()
        
        state = AsyncMock()
        state.get_state.return_value = None
        state.get_data.return_value = {}
        state.set_state = AsyncMock()
        state.update_data = AsyncMock()
        
        # Act
        success, result = await safe_api_call(mock_api_func, message, state)
        
        # Assert
        assert success is False
        assert result is None
        state.set_state.assert_called_once_with(CommonStates.handling_api_error)
```

### Интеграционные тесты

```python
@pytest.mark.integration
async def test_meta_state_recovery_workflow():
    """Интеграционный тест полного цикла восстановления"""
    
    # Создание мокового бота и состояния
    bot = Mock()
    state = AsyncMock()
    message = Mock()
    message.bot = bot
    message.answer = AsyncMock()
    
    # Симуляция ошибки API
    error_details = {"error": "Connection timeout", "status": 0}
    await MetaStateTransition.transition_to_api_error(message, state, error_details)
    
    # Проверка перехода в Meta-состояние
    state.set_state.assert_called_with(CommonStates.handling_api_error)
    
    # Симуляция восстановления
    with patch('app.utils.health_check.check_system_health') as mock_health:
        mock_health.return_value = {
            "api_connection": True,
            "database_accessible": True
        }
        
        # Симуляция команды /retry
        message.text = "/retry"
        await handle_api_error_state(message, state)
        
        # Проверка восстановления
        state.clear.assert_called_once()
        message.answer.assert_called_with("✅ Соединение восстановлено! Можете продолжить работу.")
```

## API для разработчиков

### Декораторы для защиты обработчиков

```python
# utils/decorators.py

def with_meta_state_protection(error_context: str = ""):
    """Декоратор для автоматической защиты обработчиков"""
    
    def decorator(handler_func):
        @wraps(handler_func)
        async def wrapper(message_or_callback, state: FSMContext, *args, **kwargs):
            try:
                return await handler_func(message_or_callback, state, *args, **kwargs)
            except Exception as e:
                logger.error(f"Error in handler {handler_func.__name__}: {e}")
                
                error_details = {
                    "error": f"Handler error in {error_context}: {str(e)}",
                    "status": 0
                }
                
                await MetaStateTransition.transition_to_api_error(
                    message_or_callback, state, error_details
                )
        
        return wrapper
    return decorator

# Использование
@with_meta_state_protection("изучение слов")
async def cmd_study(message: Message, state: FSMContext):
    # Обработчик автоматически защищен от ошибок
    pass
```

### Утилиты для мониторинга

```python
# utils/meta_state_monitor.py

class MetaStateMonitor:
    """Мониторинг Meta-состояний"""
    
    def __init__(self):
        self.metrics = {
            "api_errors": 0,
            "connection_lost": 0,
            "unknown_commands": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0
        }
    
    def record_error(self, error_type: str):
        """Запись ошибки"""
        if error_type in self.metrics:
            self.metrics[error_type] += 1
    
    def record_recovery(self, success: bool):
        """Запись попытки восстановления"""
        if success:
            self.metrics["successful_recoveries"] += 1
        else:
            self.metrics["failed_recoveries"] += 1
    
    def get_stats(self) -> dict:
        """Получение статистики"""
        total_errors = sum(v for k, v in self.metrics.items() if k.endswith("_errors") or k == "connection_lost")
        total_recoveries = self.metrics["successful_recoveries"] + self.metrics["failed_recoveries"]
        
        return {
            **self.metrics,
            "total_errors": total_errors,
            "recovery_rate": (
                self.metrics["successful_recoveries"] / total_recoveries
                if total_recoveries > 0 else 0
            )
        }

# Глобальный экземпляр монитора
meta_state_monitor = MetaStateMonitor()
```

---

**Meta-состояния обеспечивают надежность системы за счет автоматической обработки ошибок и graceful recovery. Используйте предоставленные инструменты для создания устойчивых к сбоям обработчиков.**

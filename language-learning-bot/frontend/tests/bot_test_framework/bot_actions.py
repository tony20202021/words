"""
Bot Test Framework - классы для моделирования действий пользователя с ботом.
"""

from typing import Any, Callable, Dict


class BotAction:
    """
    Базовый класс для моделирования действий пользователя с ботом.
    """
    async def execute(self, context: "BotTestContext") -> None:
        raise NotImplementedError("Subclasses must implement this method")


class CommandAction(BotAction):
    """
    Моделирует команду пользователя.
    """
    def __init__(self, command: str, args: str = ""):
        self.command = command
        self.args = args

    async def execute(self, context) -> None:
        await context.execute_command(self.command, self.args)


class MessageAction(BotAction):
    """
    Моделирует сообщение пользователя (не команду).
    """
    def __init__(self, text: str):
        self.text = text

    async def execute(self, context) -> None:
        await context.send_message(self.text)


class CallbackAction(BotAction):
    """
    Моделирует нажатие на inline-кнопку (callback).
    """
    def __init__(self, callback_data: str):
        self.callback_data = callback_data

    async def execute(self, context) -> None:
        await context.trigger_callback(self.callback_data)


class AssertionAction(BotAction):
    """
    Выполняет проверку состояния или результата.
    """
    def __init__(self, assertion_func: Callable[["BotTestContext"], bool], error_message: str, step_name: str = None):
        self.assertion_func = assertion_func
        self.error_message = error_message
        self.step_name = step_name

    async def execute(self, context) -> None:
        step_info = f" [Шаг: {self.step_name}]" if self.step_name else ""
        assert self.assertion_func(context), f"{self.error_message}{step_info}"
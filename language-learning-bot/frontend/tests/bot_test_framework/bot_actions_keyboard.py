"""
Расширенные действия для Bot Test Framework, включающие проверку клавиатур.
"""

from typing import Any, Callable, Dict, Optional
from .bot_actions import BotAction, AssertionAction


class AssertKeyboardContains(BotAction):
    """
    Проверяет, содержит ли клавиатура кнопку с указанным текстом или callback_data.
    """
    def __init__(self, button_text: Optional[str] = None, callback_data: Optional[str] = None, 
                 should_exist: bool = True, step_name: Optional[str] = None):
        self.button_text = button_text
        self.callback_data = callback_data
        self.should_exist = should_exist
        self.step_name = step_name

    async def execute(self, context) -> None:
        # Проверяем последнее сообщение
        if not context.sent_messages:
            assert not self.should_exist, f"Нет сообщений для проверки клавиатуры{' [Шаг: ' + self.step_name + ']' if self.step_name else ''}"
            return
        
        # Получаем kwargs последнего сообщения
        kwargs = context.sent_messages[-1][1]
        
        # Проверяем наличие клавиатуры
        if 'reply_markup' not in kwargs:
            assert not self.should_exist, f"В сообщении нет клавиатуры{' [Шаг: ' + self.step_name + ']' if self.step_name else ''}"
            return
        
        # Получаем клавиатуру
        keyboard = kwargs['reply_markup']
        
        # Проверяем тип клавиатуры
        if hasattr(keyboard, 'inline_keyboard'):
            # Inline-клавиатура
            found = False
            buttons_all = []
            for row in keyboard.inline_keyboard:
                for button in row:
                    buttons_all.append(button)

                    if (self.button_text and hasattr(button, 'text') and 
                            self.button_text in button.text):
                        found = True
                        break
                    if (self.callback_data and hasattr(button, 'callback_data') and 
                            self.callback_data in button.callback_data):
                        found = True
                        break
                if found:
                    break
            
            if (found != self.should_exist):
                print(buttons_all)

            assert found == self.should_exist, f"{'Не найдена' if self.should_exist else 'Найдена'} кнопка {self.button_text or self.callback_data} в клавиатуре{' [Шаг: ' + self.step_name + ']' if self.step_name else ''}, buttons_all={buttons_all}"
        else:
            # Обычная клавиатура
            found = False
            buttons_all = []
            for row in keyboard.keyboard:
                for button in row:
                    buttons_all.append(button)

                    if self.button_text and hasattr(button, 'text') and self.button_text in button.text:
                        found = True
                        break
                if found:
                    break
            
            if (found != self.should_exist):
                print(buttons_all)

            assert found == self.should_exist, f"{'Не найдена' if self.should_exist else 'Найдена'} кнопка {self.button_text} в клавиатуре{' [Шаг: ' + self.step_name + ']' if self.step_name else ''}, buttons_all={buttons_all}"


class AssertKeyboardNotContains(BotAction):
    """
    Проверяет, что клавиатура НЕ содержит кнопку с указанным текстом или callback_data.
    """
    def __init__(self, button_text: Optional[str] = None, callback_data: Optional[str] = None, 
                 step_name: Optional[str] = None):
        self.button_text = button_text
        self.callback_data = callback_data
        self.step_name = step_name

    async def execute(self, context) -> None:
        # Используем AssertKeyboardContains с инвертированной логикой
        keyboard_checker = AssertKeyboardContains(
            button_text=self.button_text,
            callback_data=self.callback_data,
            should_exist=False,
            step_name=self.step_name
        )
        await keyboard_checker.execute(context)


class AssertKeyboardButtonCount(BotAction):
    """
    Проверяет, что клавиатура содержит указанное количество кнопок.
    """
    def __init__(self, expected_count: int, step_name: Optional[str] = None):
        self.expected_count = expected_count
        self.step_name = step_name

    async def execute(self, context) -> None:
        # Проверяем последнее сообщение
        if not context.sent_messages:
            assert False, f"Нет сообщений для проверки клавиатуры{' [Шаг: ' + self.step_name + ']' if self.step_name else ''}"
            return
        
        # Получаем kwargs последнего сообщения
        kwargs = context.sent_messages[-1][1]
        
        # Проверяем наличие клавиатуры
        if 'reply_markup' not in kwargs:
            assert False, f"В сообщении нет клавиатуры{' [Шаг: ' + self.step_name + ']' if self.step_name else ''}"
            return
        
        # Получаем клавиатуру
        keyboard = kwargs['reply_markup']
        
        # Проверяем тип клавиатуры и считаем кнопки
        actual_count = 0
        buttons_all = []
        
        if hasattr(keyboard, 'inline_keyboard'):
            # Inline-клавиатура
            for row in keyboard.inline_keyboard:
                buttons_all.append(row)
                actual_count += len(row)
        else:
            # Обычная клавиатура
            for row in keyboard.keyboard:
                buttons_all.append(row)
                actual_count += len(row)
        
        assert actual_count == self.expected_count, f"Ожидалось {self.expected_count} кнопок, но найдено {actual_count}{' [Шаг: ' + self.step_name + ']' if self.step_name else ''}, buttons_all={buttons_all}"
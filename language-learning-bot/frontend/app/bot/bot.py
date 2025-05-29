"""
Telegram bot manager class.
This class is responsible for handling the bot instance and dispatcher.
"""

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

BOT_COMMANDS = [
    {"command": "start", "description": "Начать работу с ботом"},
    {"command": "help", "description": "Получить справку"},
    {"command": "stats", "description": "Показать статистику"},
    {"command": "hint", "description": "Информация о подсказках"},
    {"command": "admin", "description": "Режим администратора"},
]

class BotManager:
    """Bot manager class to handle bot instance and dispatcher."""
    
    def __init__(self, bot: Bot, dp: Dispatcher):
        """
        Initialize the bot manager.
        
        Args:
            bot: Bot instance
            dp: Dispatcher instance
        """
        self.bot = bot
        self.dp = dp
        
    async def setup_commands(self):
        """
        Set up bot commands for easy access in Telegram client.
        """
        commands = [BotCommand(command=cmd["command"], description=cmd["description"]) 
                   for cmd in BOT_COMMANDS]
        
        await self.bot.set_my_commands(commands)
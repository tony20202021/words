"""
Script for managing admin users in the Language Learning Bot using API client.
This script allows finding, displaying, promoting users to admin status,
and listing all users in the system.
"""

import asyncio
import os
import sys
import argparse
from datetime import datetime
from dotenv import load_dotenv

# Добавляем корневой каталог проекта в путь Python для импорта
# Предполагаем, что скрипт находится в каталоге scripts/ в корне проекта
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

# Теперь импортируем APIClient из проекта
from frontend.app.api.client import APIClient

# Загрузка переменных окружения
load_dotenv()

# Получаем параметры подключения к API из переменных окружения
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8500")
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "10"))

async def find_user_by_telegram_id(api_client, telegram_id):
    """
    Find a user by their Telegram ID using API client.
    
    Args:
        api_client: API client instance
        telegram_id: Telegram ID of the user
        
    Returns:
        User document or None if not found
    """
    user = await api_client.get_user_by_telegram_id(int(telegram_id))
    return user

async def list_all_users(api_client, limit=100):
    """
    List all users using API client.
    
    Args:
        api_client: API client instance
        limit: Maximum number of users to list
    """
    # Используем метод, который возвращает всех пользователей
    # Предполагаем, что API поддерживает пагинацию через параметры skip и limit
    request_result = await api_client._make_request("GET", "/users", params={"skip": 0, "limit": limit}) or []
    users = request_result['result']

    if not users:
        print("No users found")
        return
    
    print(f"\n------ All Users ({len(users)}) ------")
    for i, user in enumerate(users, 1):
        print(f"{i}. ID: {user.get('id', 'N/A')}, "
              f"Telegram ID: {user.get('telegram_id', 'N/A')}, "
              f"Username: {user.get('username', 'N/A')}, "
              f"Admin: {user.get('is_admin', False)}")
    print("------------------------------\n")
    
    return users

async def display_user_info(user):
    """
    Display information about a user.
    
    Args:
        user: User document
    """
    if not user:
        print("User not found")
        return
    
    print("\n------ User Information ------")
    print(f"User ID: {user.get('id', 'Not available')}")
    print(f"Telegram ID: {user.get('telegram_id', 'Not available')}")
    print(f"Username: {user.get('username', 'Not set')}")
    print(f"First Name: {user.get('first_name', 'Not set')}")
    print(f"Last Name: {user.get('last_name', 'Not set')}")
    print(f"Is Admin: {user.get('is_admin', False)}")
    print(f"Created At: {user.get('created_at', 'Not set')}")
    print(f"Updated At: {user.get('updated_at', 'Not set')}")
    print("------------------------------\n")

async def make_user_admin(api_client, user_id):
    """
    Make a user an admin using API client.
    
    Args:
        api_client: API client instance
        user_id: User ID
        
    Returns:
        True if successful, False otherwise
    """
    update_data = {
        "is_admin": True
    }
    
    result = await api_client.update_user(user_id, update_data)
    
    if result:
        print(f"User {user_id} is now an admin!")
        return True
    else:
        print(f"Failed to update user {user_id}")
        return False

async def main():
    parser = argparse.ArgumentParser(description="Manage admin users for Language Learning Bot using API client")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Find user by Telegram ID
    find_parser = subparsers.add_parser("find", help="Find user by Telegram ID")
    find_parser.add_argument("telegram_id", type=int, help="Telegram ID of the user")
    
    # Display user info
    info_parser = subparsers.add_parser("info", help="Display user information")
    info_parser.add_argument("telegram_id", type=int, help="Telegram ID of the user")
    
    # Make user admin
    admin_parser = subparsers.add_parser("make-admin", help="Make user an admin")
    admin_parser.add_argument("user_id", type=str, help="User ID")
    
    # Combination command to do all three steps
    promote_parser = subparsers.add_parser("promote", help="Find, display info, and make a user admin")
    promote_parser.add_argument("telegram_id", type=int, help="Telegram ID of the user")
    
    # List all users
    list_parser = subparsers.add_parser("list", help="List all users")
    list_parser.add_argument("--limit", type=int, default=100, help="Maximum number of users to list")
    
    args = parser.parse_args()
    
    # Initialize API client
    api_client = APIClient(base_url=BACKEND_URL, timeout=API_TIMEOUT)
    
    if args.command == "find":
        user = await find_user_by_telegram_id(api_client, args.telegram_id)
        if user:
            print(f"User found! ID: {user['id']}")
            await display_user_info(user)
        else:
            print(f"No user found with Telegram ID {args.telegram_id}")
            
    elif args.command == "info":
        user = await find_user_by_telegram_id(api_client, args.telegram_id)
        if user:
            await display_user_info(user)
        else:
            print(f"No user found with Telegram ID {args.telegram_id}")
        
    elif args.command == "make-admin":
        success = await make_user_admin(api_client, args.user_id)
        
    elif args.command == "promote":
        user = await find_user_by_telegram_id(api_client, args.telegram_id)
        if not user:
            print(f"No user found with Telegram ID {args.telegram_id}")
            return
            
        print(f"User found! ID: {user['id']}")
        await display_user_info(user)
        
        # Подтверждение перед назначением администратором
        confirm = input("Make this user an admin? [y/N]: ")
        if confirm.lower() == 'y':
            await make_user_admin(api_client, user['id'])
            # Отображение обновленной информации
            updated_user = await find_user_by_telegram_id(api_client, args.telegram_id)
            await display_user_info(updated_user)
        else:
            print("Operation canceled")
    
    elif args.command == "list":
        await list_all_users(api_client, args.limit)
    
    else:
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main())

# Как использовать:
# bash# Вывести список всех пользователей
# python scripts/admin_manager.py list

# # Найти пользователя по Telegram ID
# python scripts/admin_manager.py find YOUR_TELEGRAM_ID

# # Сделать пользователя администратором
# python scripts/admin_manager.py make-admin USER_ID

# # Найти и сделать пользователя администратором
# python scripts/admin_manager.py promote YOUR_TELEGRAM_ID
# Если структура вашего проекта отличается от предполагаемой (то есть скрипт находится в каталоге scripts/ в корне проекта, а клиент API — в frontend/app/api/client.py), вам нужно будет скорректировать пути для импорта.
"""
Admin messaging handlers for broadcasting messages to all users.
Handles message composition, confirmation, and sending with progress tracking.
"""

import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.utils.callback_constants import CallbackData
from app.bot.states.centralized_states import AdminStates
from app.utils.admin_utils import is_user_admin

# Создаем роутер для обработчиков рассылки сообщений
messaging_router = Router()

logger = setup_logger(__name__)


@messaging_router.callback_query(AdminStates.main_menu, F.data == CallbackData.ADMIN_SEND_MESSAGE_TO_ALL)
async def process_admin_send_message_to_all(callback: CallbackQuery, state: FSMContext):
    """
    Handle the 'admin_send_message_to_all' callback which starts message composition.

    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    user_id = callback.from_user.id
    username = callback.from_user.username
    full_name = callback.from_user.full_name

    logger.info(f"'admin_send_message_to_all' callback from {full_name} ({username})")

    # Проверяем права администратора
    if not await is_user_admin(callback, state):
        await callback.answer("У вас нет прав администратора.", show_alert=True)
        return

    await callback.message.answer(
        "📝 <b>Рассылка сообщения всем пользователям</b>\n\n"
        "Введите текст сообщения, которое будет отправлено всем пользователям с включенными уведомлениями:",
        parse_mode="HTML"
    )
    
    await state.set_state(AdminStates.sending_message_to_all)
    await callback.answer()


@messaging_router.message(AdminStates.sending_message_to_all)
async def process_admin_send_message_to_all_message(message: Message, state: FSMContext):
    """
    Handle the message text input and show confirmation.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name

    message_text = message.text

    logger.info(f"Message composition from {full_name} ({username})")
    logger.info(f"Message text: {message_text}")

    # Проверяем права администратора
    if not await is_user_admin(message, state):
        await message.answer("У вас нет прав администратора.")
        return

    # Получаем клиент API
    api_client = get_api_client_from_bot(message.bot)

    # Получаем список всех пользователей
    all_users_response = await api_client.get_users(skip=0, limit=1000)

    if not all_users_response["success"]:
        await message.answer("❌ Ошибка при получении списка пользователей")
        return

    all_users = all_users_response["result"] or []
    
    # Подсчитываем пользователей с включенными уведомлениями
    eligible_users = []
    admin_telegram_id = message.from_user.id
    active_languages = {}
    
    # Получаем список языков для проверки настроек
    languages_response = await api_client.get_languages()
    languages = languages_response["result"] if languages_response["success"] else []
    
    for user in all_users:
        # Исключаем самого администратора
        if user.get("telegram_id") == admin_telegram_id:
            logger.info(f"Skipping admin user: {user.get('first_name')} ({user.get('telegram_id')})")
            continue
            
        # Получаем настройки пользователя для всех языков
        user_db_id = user.get("id") or user.get("_id")
        if not user_db_id:
            continue
            
        # Проверяем настройки по всем языкам
        has_notifications_enabled = False
        active_languages[user.get("telegram_id")] = []
        
        for language in languages:
            language_id = language.get("id") or language.get("_id")
            if not language_id:
                continue
                
            settings_response = await api_client.get_user_language_settings(user_db_id, language_id)
            
            if settings_response["success"] and settings_response["result"]:
                settings = settings_response["result"]
                if settings.get("receive_messages", True):  # По умолчанию True
                    has_notifications_enabled = True
                    active_languages[user.get("telegram_id")].append(language.get("name"))
                
        # Если не было найдено ни одного языка, считаем что уведомления включены
        if not languages:
            has_notifications_enabled = True
        
        if has_notifications_enabled:
            eligible_users.append(user)

    # Сохраняем данные в состоянии
    await state.update_data(
        message_text=message_text,
        eligible_users=eligible_users,
        active_languages=active_languages
    )

    # Создаем клавиатуру подтверждения
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Отправить", 
                callback_data=CallbackData.CONFIRM_MESSAGING
            ),
            InlineKeyboardButton(
                text="❌ Отменить", 
                callback_data=CallbackData.CANCEL_MESSAGING
            )
        ]
    ])

    # Показываем подтверждение
    users_list = '\n'.join([f"{user.get('username')} ({user.get('telegram_id')})" for user in eligible_users])
    confirmation_text = (
        f"📋 <b>Подтверждение рассылки</b>\n\n"
        f"<b>Текст сообщения:</b>\n"
        f"<code>{message_text}</code>\n\n"
        f"👥 <b>Получателей:</b> {len(eligible_users)} пользователей:\n"
        f"{users_list}\n\n"
        f"Отправить сообщение?"
    )

    await message.answer(
        confirmation_text,
        parse_mode="HTML",
        reply_markup=keyboard
    )
    
    await state.set_state(AdminStates.confirming_message_send)


@messaging_router.callback_query(AdminStates.confirming_message_send, F.data == CallbackData.CONFIRM_MESSAGING)
async def process_confirm_messaging(callback: CallbackQuery, state: FSMContext):
    """
    Handle confirmation of message sending and start the sending process.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    user_id = callback.from_user.id
    username = callback.from_user.username
    full_name = callback.from_user.full_name

    logger.info(f"Message sending confirmed by {full_name} ({username})")

    # Получаем данные из состояния
    state_data = await state.get_data()
    message_text = state_data.get("message_text")
    eligible_users = state_data.get("eligible_users", [])
    active_languages = state_data.get("active_languages", [])

    if not message_text or not eligible_users:
        await callback.answer("❌ Ошибка: данные сообщения не найдены", show_alert=True)
        return

    await state.set_state(AdminStates.processing_message_send)
    await callback.answer()

    # Начинаем процесс отправки
    await send_messages_to_users(callback.message, message_text, eligible_users, active_languages, state)


@messaging_router.callback_query(AdminStates.confirming_message_send, F.data == CallbackData.CANCEL_MESSAGING)
async def process_cancel_messaging(callback: CallbackQuery, state: FSMContext):
    """
    Handle cancellation of message sending.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    user_id = callback.from_user.id
    username = callback.from_user.username
    full_name = callback.from_user.full_name

    logger.info(f"Message sending cancelled by {full_name} ({username})")

    await callback.message.answer("❌ Рассылка сообщения отменена.")
    await callback.answer()

    # Возвращаемся в админ меню
    from app.bot.handlers.admin.admin_basic_handlers import handle_admin_mode
    await handle_admin_mode(callback, state, is_callback=True)


async def send_messages_to_users(message: Message, message_text: str, eligible_users: list, active_languages: dict, state: FSMContext):
    """
    Send messages to all eligible users with progress tracking.
    
    Args:
        message: The message object for sending progress updates
        message_text: Text to send to users
        eligible_users: List of users to send message to
        active_languages: Dictionary of active languages for each user
        state: The FSM state context
    """
    total_users = len(eligible_users)
    sent_count = 0
    error_count = 0
    failed_users = []

    logger.info(f"Starting message broadcast to {total_users} users")

    # Отправляем начальное сообщение о прогрессе
    progress_message = await message.answer(
        f"📤 <b>Рассылка в процессе...</b>\n"
        f"✅ Отправлено: 0\n"
        f"❌ Ошибок: 0\n"
        f"📊 Прогресс: 0/{total_users} (0%)",
        parse_mode="HTML"
    )

    # Отправляем сообщения пользователям
    for i, user in enumerate(eligible_users):
        try:
            user_telegram_id = user.get("telegram_id")
            user_name = user.get("first_name", "Пользователь")
            active_languages_text = "\n".join(active_languages.get(user_telegram_id, []))
            
            if user_telegram_id:
                await message.bot.send_message(user_telegram_id, message_text + f"\n\n🔍 <b>Активные языки:</b>\n{active_languages_text}")
                sent_count += 1
                logger.info(f"Message sent to {user_name} ({user_telegram_id})")
            else:
                error_count += 1
                failed_users.append(f"{user_name} (нет Telegram ID)")
                logger.warning(f"No Telegram ID for user {user_name}")

        except Exception as e:
            error_count += 1
            user_name = user.get("first_name", "Неизвестный")
            failed_users.append(f"{user_name} ({str(e)[:50]})")
            logger.error(f"Failed to send message to {user_name}: {e}")

        # Обновляем прогресс каждые 5 пользователей или на последнем
        if (i + 1) % 5 == 0 or i == total_users - 1:
            progress_percentage = int(((i + 1) / total_users) * 100)
            
            try:
                await progress_message.edit_text(
                    f"📤 <b>Рассылка в процессе...</b>\n"
                    f"✅ Отправлено: {sent_count}\n"
                    f"❌ Ошибок: {error_count}\n"
                    f"📊 Прогресс: {i + 1}/{total_users} ({progress_percentage}%)",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.warning(f"Failed to update progress message: {e}")

        # Задержка между отправками
        await asyncio.sleep(0.1)

    # Финальный отчет
    final_message = (
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"📊 <b>Статистика:</b>\n"
        f"✅ Успешно отправлено: {sent_count}\n"
        f"❌ Ошибок: {error_count}\n"
        f"👥 Всего пользователей: {total_users}"
    )

    if failed_users:
        failed_list = "\n".join(failed_users[:10])  # Показываем первые 10 ошибок
        if len(failed_users) > 10:
            failed_list += f"\n... и еще {len(failed_users) - 10} ошибок"
        
        final_message += f"\n\n❌ <b>Ошибки отправки:</b>\n<code>{failed_list}</code>"

    try:
        await progress_message.edit_text(final_message, parse_mode="HTML")
    except Exception as e:
        # Если не удалось обновить, отправляем новое сообщение
        await message.answer(final_message, parse_mode="HTML")

    logger.info(f"Message broadcast completed: {sent_count} sent, {error_count} errors")

    # Возвращаемся в админ меню
    from app.bot.handlers.admin.admin_basic_handlers import handle_admin_mode
    await handle_admin_mode(message, state, is_callback=False)

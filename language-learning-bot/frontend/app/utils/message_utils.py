from aiogram.types import Message, CallbackQuery


def get_user_info(message_or_callback) -> tuple:

    user_id = message_or_callback.from_user.id
    username = message_or_callback.from_user.username
    full_name = message_or_callback.from_user.full_name

    return user_id, username, full_name


def get_message_from_callback(message_or_callback) -> Message:

    if isinstance(message_or_callback, CallbackQuery):
        message = message_or_callback.message
    else:
        message = message_or_callback

    return message

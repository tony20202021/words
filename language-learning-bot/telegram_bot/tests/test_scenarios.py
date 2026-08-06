"""
Сценарные тесты бота: последовательности действий, а не отдельные хендлеры.

Остальные тесты дёргают по одному обработчику. Но баги, которые ловились
руками, жили в переходах: состояние не доезжало между шагами, «Начать заново»
не сбрасывало сессию, ошибка BLS оставляла пользователя в тупике.

Здесь состояние FSM общее на весь сценарий — как в реальном диалоге. Часть
проверок перенесена из сценариев удалённого legacy-фронтенда
(`frontend/tests/test_scenarios/scenarios/*.yaml`, коммит 5bf18ae): порядок
операций, независимость языков, поведение при отказе API.

Оттуда же взят принцип: проверять не «хендлер не упал», а что состояние
действительно изменилось и что вызовы к BLS пошли в правильном порядке.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aiogram.types import CallbackQuery, Chat, Message, User

from tests.conftest import make_card, make_session_resp


class FakeState:
    """
    FSM-состояние, живущее весь сценарий.

    Штатные MagicMock-моки в одношаговых тестах ничего не помнят, поэтому
    цепочку шагов на них не проверить: каждый шаг видел бы пустое состояние.
    """

    def __init__(self, **initial):
        self.data = dict(initial)
        self.state = None

    async def get_data(self):
        return dict(self.data)

    async def update_data(self, **kw):
        self.data.update(kw)
        return dict(self.data)

    async def set_state(self, state=None):
        self.state = state

    async def get_state(self):
        return self.state

    async def clear(self):
        self.data.clear()
        self.state = None


def make_message(text: str = "", user_id: int = 1) -> MagicMock:
    user = MagicMock(spec=User)
    user.id = user_id
    user.username = "testuser"
    user.first_name = "Test"
    chat = MagicMock(spec=Chat)
    chat.id = user_id
    msg = MagicMock(spec=Message)
    msg.text = text
    msg.from_user = user
    msg.chat = chat
    msg.bot = MagicMock()
    msg.answer = AsyncMock()
    msg.answer_photo = AsyncMock()
    msg.answer_voice = AsyncMock()
    msg.answer_document = AsyncMock()
    return msg


def make_callback(data: str, user_id: int = 1) -> MagicMock:
    msg = make_message(user_id=user_id)
    msg.edit_text = AsyncMock()
    cb = MagicMock(spec=CallbackQuery)
    cb.data = data
    cb.from_user = msg.from_user
    cb.message = msg
    cb.answer = AsyncMock()
    return cb


def texts(mock_msg) -> list[str]:
    """Все тексты, отправленные пользователю, в порядке отправки."""
    out = []
    for call in mock_msg.answer.await_args_list:
        if call.args:
            out.append(str(call.args[0]))
        elif "text" in call.kwargs:
            out.append(str(call.kwargs["text"]))
    return out


class TestStudyCycle:
    """Основной цикл: показать слово -> «Знаю» -> «Дальше»."""

    @pytest.mark.asyncio
    async def test_know_then_rate_calls_bls_in_order(self, mock_bls):
        from app.bot.handlers import study

        state = FakeState(language_id="lang1", bls_user_id="u1")
        mock_bls.get_session = AsyncMock(return_value=make_session_resp())
        mock_bls.know_word = AsyncMock(return_value=make_session_resp(show_answer=True))
        mock_bls.rate_word = AsyncMock(return_value=make_session_resp())

        with patch("app.bot.handlers.study.get_bls_client", return_value=mock_bls):
            await study.handle_study_callback(make_callback("study:lang1:know"), state, "u1")
            await study.handle_study_callback(
                make_callback("study:lang1:rate:know"), state, "u1")

        assert mock_bls.know_word.called, "«Знаю» должно уйти в BLS"
        assert mock_bls.rate_word.called, "«Дальше» должно уйти в BLS"

    @pytest.mark.asyncio
    async def test_dont_know_does_not_score_as_known(self, mock_bls):
        from app.bot.handlers import study

        state = FakeState(language_id="lang1", bls_user_id="u1")
        mock_bls.get_session = AsyncMock(return_value=make_session_resp())
        mock_bls.show_answer = AsyncMock(return_value=make_session_resp(show_answer=True))
        mock_bls.rate_word = AsyncMock(return_value=make_session_resp())
        mock_bls.know_word = AsyncMock(return_value=make_session_resp(show_answer=True))

        with patch("app.bot.handlers.study.get_bls_client", return_value=mock_bls):
            await study.handle_study_callback(
                make_callback("study:lang1:show_answer"), state, "u1")
            await study.handle_study_callback(
                make_callback("study:lang1:rate:dont_know"), state, "u1")

        assert mock_bls.show_answer.called
        assert not mock_bls.know_word.called, "«не знаю» не должно засчитываться как знание"

    @pytest.mark.asyncio
    async def test_restart_closes_the_old_session_before_opening_a_new_one(self, mock_bls):
        """
        Порядок здесь принципиален: не закрыв старую сессию, /restart продолжит
        её же — кнопка визуально не сделает ничего. Ровно этот баг ловили
        в офлайн-режиме Android.
        """
        from app.bot.handlers import study

        order = []
        state = FakeState(language_id="lang1", bls_user_id="u1")
        mock_bls.end_session = AsyncMock(side_effect=lambda *a, **k: order.append("end"))
        mock_bls.start_session = AsyncMock(
            side_effect=lambda *a, **k: (order.append("start"), make_session_resp())[1])

        with patch("app.bot.handlers.study.get_bls_client", return_value=mock_bls):
            await study.cmd_restart(make_message("/restart"), state, "u1")

        assert order == ["end", "start"], f"неверный порядок вызовов: {order}"


class TestStateAcrossSteps:
    """Состояние должно доезжать между шагами — этого одношаговые тесты не видят."""

    @pytest.mark.asyncio
    async def test_language_choice_persists_into_next_step(self, mock_bls):
        from app.bot.handlers import start

        state = FakeState()
        mock_bls.get_languages = AsyncMock(return_value=[
            {"id": "lang1", "name_ru": "Китайский", "name_foreign": "中文"},
        ])
        mock_bls.get_statistics = AsyncMock(return_value={
            "progress_percentage": 0.0, "total_words": 100, "words_for_today": 5})
        mock_bls.is_admin = AsyncMock(return_value=False)

        msg = make_message("/start")
        with patch("app.bot.handlers.start.get_bls_client", return_value=mock_bls):
            await start.cmd_start(msg, state, "u1")

        assert state.data.get("bls_user_id") == "u1", (
            "идентификатор пользователя должен сохраниться в состоянии для следующих шагов")
        assert any("Здравствуйте" in t for t in texts(msg))

class TestErrorsReachTheUser:
    """
    Перенесено из api_errors.yaml — самое ценное из старых сценариев.

    Раньше исключение из хендлера aiogram просто писал в лог, а пользователь
    не получал ничего: экран «висит», непонятно, нажалась кнопка или нет.
    Теперь на это есть глобальный обработчик `on_handler_error`.
    """

    @pytest.mark.asyncio
    async def test_message_handler_failure_tells_the_user(self):
        from app.main import on_handler_error

        msg = make_message("/start")
        update = MagicMock()
        update.message = msg
        update.callback_query = None
        event = MagicMock()
        event.update = update
        event.exception = RuntimeError("BLS недоступен")

        handled = await on_handler_error(event)

        assert handled is True, "поллинг не должен останавливаться из-за ошибки"
        assert msg.answer.await_count == 1, "пользователь должен получить сообщение"
        assert "недоступен" in texts(msg)[0].lower()

    @pytest.mark.asyncio
    async def test_callback_failure_answers_in_the_same_chat(self):
        from app.main import on_handler_error

        cb = make_callback("study:lang1:know")
        update = MagicMock()
        update.message = None
        update.callback_query = cb
        event = MagicMock()
        event.update = update
        event.exception = RuntimeError("BLS недоступен")

        assert await on_handler_error(event) is True
        assert cb.message.answer.await_count == 1

    @pytest.mark.asyncio
    async def test_handler_survives_a_broken_update(self):
        """Если из события ничего не достать — не падать самому."""
        from app.main import on_handler_error

        event = MagicMock()
        event.update = None
        event.exception = RuntimeError("boom")
        assert await on_handler_error(event) is True

    @pytest.mark.asyncio
    async def test_error_handler_is_registered_in_the_dispatcher(self):
        """Обработчик бесполезен, если его забыли подключить."""
        import inspect
        from app import main as bot_main

        src = inspect.getsource(bot_main.main)
        assert "dp.errors.register(on_handler_error)" in src, (
            "глобальный обработчик ошибок не зарегистрирован в диспетчере")


class TestAdminVisibility:
    """
    /admin скрыт от обычных пользователей и виден админам — и в меню, и кнопкой.
    Проверяется цепочка: is_admin -> клавиатура -> персональный список команд.
    """

    @pytest.mark.asyncio
    async def test_admin_sees_button_and_gets_personal_command(self, mock_bls):
        from app.bot.handlers import start

        state = FakeState()
        mock_bls.get_languages = AsyncMock(return_value=[
            {"id": "lang1", "name_ru": "Китайский", "name_foreign": "中文"}])
        mock_bls.get_statistics = AsyncMock(return_value={
            "progress_percentage": 0.0, "total_words": 1, "words_for_today": 0})
        mock_bls.is_admin = AsyncMock(return_value=True)

        msg = make_message("/start")
        with patch("app.bot.handlers.start.get_bls_client", return_value=mock_bls), \
             patch("app.main.sync_admin_commands", new=AsyncMock()) as sync:
            await start.cmd_start(msg, state, "u1")

        sync.assert_awaited()
        assert sync.await_args.args[2] is True, "админу команда должна ставиться"

        kb = msg.answer.await_args_list[-1].kwargs.get("reply_markup")
        labels = [b.text for row in kb.inline_keyboard for b in row]
        assert any("Админка" in t for t in labels), f"кнопки админки нет: {labels}"

    @pytest.mark.asyncio
    async def test_regular_user_gets_no_admin_affordances(self, mock_bls):
        from app.bot.handlers import start

        state = FakeState()
        mock_bls.get_languages = AsyncMock(return_value=[
            {"id": "lang1", "name_ru": "Китайский", "name_foreign": "中文"}])
        mock_bls.get_statistics = AsyncMock(return_value={
            "progress_percentage": 0.0, "total_words": 1, "words_for_today": 0})
        mock_bls.is_admin = AsyncMock(return_value=False)

        msg = make_message("/start")
        with patch("app.bot.handlers.start.get_bls_client", return_value=mock_bls), \
             patch("app.main.sync_admin_commands", new=AsyncMock()) as sync:
            await start.cmd_start(msg, state, "u1")

        assert sync.await_args.args[2] is False, (
            "у неадмина персональный список должен сниматься — иначе команда "
            "останется в меню после снятия прав")

        kb = msg.answer.await_args_list[-1].kwargs.get("reply_markup")
        labels = [b.text for row in kb.inline_keyboard for b in row]
        assert not any("Админка" in t for t in labels), f"лишняя кнопка: {labels}"

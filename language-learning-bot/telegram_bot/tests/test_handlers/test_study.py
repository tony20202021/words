"""Unit tests for study callback handler."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import CallbackQuery, Message, User, Chat
from tests.conftest import make_card, make_session_resp


def make_callback(data: str, user_id: int = 1) -> CallbackQuery:
    user = MagicMock(spec=User)
    user.id = user_id
    user.username = "testuser"
    msg = MagicMock(spec=Message)
    msg.edit_text = AsyncMock()
    cb = MagicMock(spec=CallbackQuery)
    cb.data = data
    cb.from_user = user
    cb.message = msg
    cb.answer = AsyncMock()
    return cb


def make_state(language_id: str = "lang1") -> MagicMock:
    state = MagicMock()
    state.get_data = AsyncMock(return_value={"language_id": language_id})
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    return state


@pytest.mark.asyncio
async def test_know_callback_calls_bls_know(mock_bls):
    from app.bot.handlers.study import handle_study_callback
    cb = make_callback("study:lang1:know")
    state = make_state()

    with patch("app.bot.handlers.study.get_bls_client", return_value=mock_bls):
        await handle_study_callback(cb, state, bls_user_id="user-1")

    mock_bls.know_word.assert_called_once_with("sess-1")
    cb.message.edit_text.assert_called_once()
    cb.answer.assert_called_once()


@pytest.mark.asyncio
async def test_show_answer_callback_calls_bls_show_answer(mock_bls):
    from app.bot.handlers.study import handle_study_callback
    cb = make_callback("study:lang1:show_answer")
    state = make_state()

    with patch("app.bot.handlers.study.get_bls_client", return_value=mock_bls):
        await handle_study_callback(cb, state, bls_user_id="user-1")

    mock_bls.show_answer.assert_called_once_with("sess-1")
    cb.message.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_rate_dont_know_callback(mock_bls):
    from app.bot.handlers.study import handle_study_callback
    cb = make_callback("study:lang1:rate:dont_know")
    state = make_state()

    with patch("app.bot.handlers.study.get_bls_client", return_value=mock_bls):
        await handle_study_callback(cb, state, bls_user_id="user-1")

    mock_bls.rate_word.assert_called_once_with("sess-1", "dont_know")


@pytest.mark.asyncio
async def test_rate_know_callback(mock_bls):
    from app.bot.handlers.study import handle_study_callback
    cb = make_callback("study:lang1:rate:know")
    state = make_state()

    with patch("app.bot.handlers.study.get_bls_client", return_value=mock_bls):
        await handle_study_callback(cb, state, bls_user_id="user-1")

    mock_bls.rate_word.assert_called_once_with("sess-1", "know")


@pytest.mark.asyncio
async def test_toggle_skip_callback(mock_bls):
    from app.bot.handlers.study import handle_study_callback
    cb = make_callback("study:lang1:toggle_skip")
    state = make_state()

    with patch("app.bot.handlers.study.get_bls_client", return_value=mock_bls):
        await handle_study_callback(cb, state, bls_user_id="user-1")

    mock_bls.toggle_skip.assert_called_once_with("sess-1")


@pytest.mark.asyncio
async def test_session_not_found_shows_alert(mock_bls):
    from app.bot.handlers.study import handle_study_callback
    mock_bls.get_session.return_value = None
    cb = make_callback("study:lang1:know")
    state = make_state()

    with patch("app.bot.handlers.study.get_bls_client", return_value=mock_bls):
        await handle_study_callback(cb, state, bls_user_id="user-1")

    cb.answer.assert_called_once()
    assert cb.answer.call_args.kwargs.get("show_alert") is True
    cb.message.edit_text.assert_not_called()


@pytest.mark.asyncio
async def test_batch_exhausted_loads_next_batch(mock_bls):
    from app.bot.handlers.study import handle_study_callback
    mock_bls.rate_word.return_value = {
        "session_id": "sess-1", "card": None, "batch_exhausted": True
    }
    mock_bls.next_batch.return_value = {"loaded": True, **make_session_resp()}

    cb = make_callback("study:lang1:rate:dont_know")
    state = make_state()

    with patch("app.bot.handlers.study.get_bls_client", return_value=mock_bls):
        await handle_study_callback(cb, state, bls_user_id="user-1")

    mock_bls.next_batch.assert_called_once_with("sess-1")
    cb.message.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_batch_exhausted_no_more_words_shows_completed(mock_bls):
    from app.bot.handlers.study import handle_study_callback, COMPLETED_TEXT
    mock_bls.rate_word.return_value = {
        "session_id": "sess-1", "card": None, "batch_exhausted": True
    }
    mock_bls.next_batch.return_value = {"loaded": False}

    cb = make_callback("study:lang1:rate:dont_know")
    state = make_state()

    with patch("app.bot.handlers.study.get_bls_client", return_value=mock_bls):
        await handle_study_callback(cb, state, bls_user_id="user-1")

    call_args = cb.message.edit_text.call_args
    assert COMPLETED_TEXT in call_args.args[0]

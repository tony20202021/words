"""Unit tests for study handler (command + callback)."""

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
    msg.answer = AsyncMock()
    msg.answer_voice = AsyncMock()
    msg.answer_audio = AsyncMock()
    msg.answer_photo = AsyncMock()
    cb = MagicMock(spec=CallbackQuery)
    cb.data = data
    cb.from_user = user
    cb.message = msg
    cb.answer = AsyncMock()
    return cb


def make_message(text="") -> MagicMock:
    msg = MagicMock(spec=Message)
    msg.text = text
    msg.answer = AsyncMock()
    return msg


def make_state(language_id: str = "lang1") -> MagicMock:
    state = MagicMock()
    state.get_data = AsyncMock(return_value={"language_id": language_id})
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    return state


# ── /study command ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cmd_study_no_language_set(mock_bls):
    from app.bot.handlers.study import cmd_study
    msg = make_message()
    state = make_state(language_id=None)
    state.get_data = AsyncMock(return_value={})
    with patch("app.bot.handlers.study.get_bls_client", return_value=mock_bls):
        await cmd_study(msg, state, bls_user_id="user-1")
    msg.answer.assert_called_once()
    assert "язык" in msg.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_cmd_study_starts_new_session(mock_bls):
    from app.bot.handlers.study import cmd_study
    mock_bls.get_session.return_value = None
    mock_bls.start_session.return_value = make_session_resp()
    msg = make_message()
    state = make_state()
    with patch("app.bot.handlers.study.get_bls_client", return_value=mock_bls):
        await cmd_study(msg, state, bls_user_id="user-1")
    mock_bls.start_session.assert_called_once()
    msg.answer.assert_called_once()


@pytest.mark.asyncio
async def test_cmd_study_reuses_existing_session(mock_bls):
    from app.bot.handlers.study import cmd_study
    mock_bls.get_session.return_value = make_session_resp()
    msg = make_message()
    state = make_state()
    with patch("app.bot.handlers.study.get_bls_client", return_value=mock_bls):
        await cmd_study(msg, state, bls_user_id="user-1")
    mock_bls.start_session.assert_not_called()
    msg.answer.assert_called_once()


@pytest.mark.asyncio
async def test_cmd_study_no_words_shows_done(mock_bls):
    from app.bot.handlers.study import cmd_study
    mock_bls.get_session.return_value = None
    mock_bls.start_session.return_value = None
    msg = make_message()
    state = make_state()
    with patch("app.bot.handlers.study.get_bls_client", return_value=mock_bls):
        await cmd_study(msg, state, bls_user_id="user-1")
    msg.answer.assert_called_once()
    assert "изучен" in msg.answer.call_args[0][0].lower() or "🎉" in msg.answer.call_args[0][0]


# ── callbacks ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_know_callback_calls_bls_know(mock_bls):
    from app.bot.handlers.study import handle_study_callback
    cb = make_callback("study:lang1:know")
    state = make_state()

    with patch("app.bot.handlers.study.get_bls_client", return_value=mock_bls):
        await handle_study_callback(cb, state, bls_user_id="user-1")

    mock_bls.know_word.assert_called_once_with("sess-1")
    cb.message.answer.assert_called_once()   # know → новое сообщение
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


# ── /restart command ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cmd_restart_no_language_set(mock_bls):
    from app.bot.handlers.study import cmd_restart
    msg = make_message()
    state = make_state(language_id=None)
    state.get_data = AsyncMock(return_value={})
    with patch("app.bot.handlers.study.get_bls_client", return_value=mock_bls):
        await cmd_restart(msg, state, bls_user_id="user-1")
    msg.answer.assert_called_once()
    assert "язык" in msg.answer.call_args[0][0].lower()
    mock_bls.end_session.assert_not_called()


@pytest.mark.asyncio
async def test_cmd_restart_ends_and_restarts_session(mock_bls):
    from app.bot.handlers.study import cmd_restart
    mock_bls.end_session = AsyncMock(return_value=None)
    mock_bls.start_session.return_value = make_session_resp()
    msg = make_message()
    state = make_state()
    with patch("app.bot.handlers.study.get_bls_client", return_value=mock_bls):
        await cmd_restart(msg, state, bls_user_id="user-1")
    mock_bls.end_session.assert_called_once_with("user-1", "lang1")
    mock_bls.start_session.assert_called_once_with("user-1", "lang1")
    msg.answer.assert_called_once()


@pytest.mark.asyncio
async def test_cmd_restart_no_words_shows_done(mock_bls):
    from app.bot.handlers.study import cmd_restart
    mock_bls.end_session = AsyncMock(return_value=None)
    mock_bls.start_session.return_value = None
    msg = make_message()
    state = make_state()
    with patch("app.bot.handlers.study.get_bls_client", return_value=mock_bls):
        await cmd_restart(msg, state, bls_user_id="user-1")
    mock_bls.end_session.assert_called_once()
    msg.answer.assert_called_once()
    assert "🎉" in msg.answer.call_args[0][0]


# ── callbacks ─────────────────────────────────────────────────────────────────

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
    cb.message.answer.assert_called_once()   # next batch loaded → новое сообщение


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

    call_args = cb.message.answer.call_args
    assert COMPLETED_TEXT in call_args.args[0]


@pytest.mark.asyncio
async def test_reconsider_callback_updates_card(mock_bls):
    from app.bot.handlers.study import handle_study_callback
    mock_bls.reconsider = AsyncMock(return_value=make_session_resp())
    cb = make_callback("study:lang1:reconsider")
    state = make_state()

    with patch("app.bot.handlers.study.get_bls_client", return_value=mock_bls):
        await handle_study_callback(cb, state, bls_user_id="user-1")

    mock_bls.reconsider.assert_called_once_with("sess-1")
    cb.message.answer.assert_called_once()   # reconsider → новое сообщение


@pytest.mark.asyncio
async def test_reconsider_batch_exhausted_loads_next(mock_bls):
    from app.bot.handlers.study import handle_study_callback
    mock_bls.reconsider = AsyncMock(return_value={
        "session_id": "sess-1", "card": None, "batch_exhausted": True
    })
    mock_bls.next_batch.return_value = {"loaded": True, **make_session_resp()}
    cb = make_callback("study:lang1:reconsider")
    state = make_state()

    with patch("app.bot.handlers.study.get_bls_client", return_value=mock_bls):
        await handle_study_callback(cb, state, bls_user_id="user-1")

    mock_bls.next_batch.assert_called_once()
    cb.message.answer.assert_called_once()   # batch loaded → новое сообщение


@pytest.mark.asyncio
async def test_reconsider_batch_exhausted_no_more_shows_completed(mock_bls):
    from app.bot.handlers.study import handle_study_callback, COMPLETED_TEXT
    mock_bls.reconsider = AsyncMock(return_value={
        "session_id": "sess-1", "card": None, "batch_exhausted": True
    })
    mock_bls.next_batch.return_value = {"loaded": False}
    cb = make_callback("study:lang1:reconsider")
    state = make_state()

    with patch("app.bot.handlers.study.get_bls_client", return_value=mock_bls):
        await handle_study_callback(cb, state, bls_user_id="user-1")

    assert COMPLETED_TEXT in cb.message.answer.call_args.args[0]


@pytest.mark.asyncio
async def test_sound_callback_sends_audio(mock_bls):
    from app.bot.handlers.study import handle_study_callback
    mock_bls.get_session.return_value = {
        "session_id": "sess-1",
        "card": {**make_card(), "sounds": ["chinese/word1.mp3"]},
    }
    mock_bls.get_sound = AsyncMock(return_value=b"\x89PNG fake audio data")
    cb = make_callback("study:lang1:sound:0")
    cb.message.answer_audio = AsyncMock()
    state = make_state()

    with patch("app.bot.handlers.study.get_bls_client", return_value=mock_bls):
        await handle_study_callback(cb, state, bls_user_id="user-1")

    mock_bls.get_sound.assert_called_once_with("chinese/word1.mp3")
    cb.message.answer_audio.assert_called_once()
    cb.message.edit_text.assert_not_called()


@pytest.mark.asyncio
async def test_sound_callback_unavailable_shows_alert(mock_bls):
    from app.bot.handlers.study import handle_study_callback
    mock_bls.get_session.return_value = {
        "session_id": "sess-1",
        "card": {**make_card(), "sounds": ["chinese/word1.mp3"]},
    }
    mock_bls.get_sound = AsyncMock(return_value=None)
    cb = make_callback("study:lang1:sound:0")
    cb.message.answer_audio = AsyncMock()
    state = make_state()

    with patch("app.bot.handlers.study.get_bls_client", return_value=mock_bls):
        await handle_study_callback(cb, state, bls_user_id="user-1")

    cb.answer.assert_called_once()
    assert cb.answer.call_args.kwargs.get("show_alert") is True
    cb.message.edit_text.assert_not_called()


# ── restart_notice ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_display_card_sends_restart_notice_separately(mock_bls):
    from app.bot.handlers.study import _display_card
    notice = "⚠️ Ошибок в сессии: 15, лимит: 10. Рекомендуется перезапустить сессию."
    card = make_card(restart_notice=notice)
    msg = make_message()

    await _display_card(msg, card, "lang1", mock_bls, edit_mode=False)

    assert msg.answer.call_count == 2
    assert msg.answer.call_args_list[0].args[0] == notice
    assert "hello" in msg.answer.call_args_list[1].args[0] or "<b>hello</b>" in msg.answer.call_args_list[1].args[0]


@pytest.mark.asyncio
async def test_display_card_skips_restart_notice_in_edit_mode(mock_bls):
    from app.bot.handlers.study import _display_card
    notice = "⚠️ Ошибок в сессии: 15, лимит: 10. Рекомендуется перезапустить сессию."
    card = make_card(restart_notice=notice, show_answer=True)
    msg = make_message()
    msg.edit_text = AsyncMock()

    await _display_card(msg, card, "lang1", mock_bls, edit_mode=True)

    msg.answer.assert_not_called()
    msg.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_display_card_sends_big_word_photo(mock_bls):
    from app.bot.handlers.study import _display_card
    card = make_card(
        show_answer=True,
        big_word={"word": "学", "transcription": "xué"},
    )
    msg = make_message()
    msg.answer_photo = AsyncMock()

    with patch("app.bot.handlers.study.generate_big_word_image", new=AsyncMock(return_value=b"png")):
        await _display_card(msg, card, "lang1", mock_bls, edit_mode=False)

    msg.answer_photo.assert_called_once()
    msg.answer.assert_called_once()

# ── звук в пик-режиме ─────────────────────────────────────────────────────────

def _session_with_sound_options(*target_texts):
    """Сессия в пик-режиме со звуковой модальностью."""
    resp = make_session_resp()
    resp["card"]["pick_options"] = {
        "target_modality": "sound",
        "options": [{"word_id": f"w{i}", "target_text": t, "is_correct": i == 0}
                    for i, t in enumerate(target_texts)],
    }
    return resp


@pytest.mark.asyncio
async def test_pick_sound_sends_every_variant_of_the_option(mock_bls):
    """
    target_text звуковой модальности — все варианты произношения через "|"
    (так их собирает quiz_service). Раньше строка целиком уходила в get_sound,
    и у слова с несколькими вариантами кнопка молча отвечала «Звук недоступен».
    """
    from app.bot.handlers.study import handle_study_callback
    mock_bls.get_session = AsyncMock(
        return_value=_session_with_sound_options("a/1.mp3|a/2.mp3", "b/1.mp3"))
    mock_bls.get_sound = AsyncMock(return_value=b"MP3")
    cb = make_callback("study:lang1:pick_sound:0")

    with patch("app.bot.handlers.study.get_bls_client", return_value=mock_bls):
        await handle_study_callback(cb, make_state(), bls_user_id="user-1")

    assert [c.args[0] for c in mock_bls.get_sound.call_args_list] == ["a/1.mp3", "a/2.mp3"]
    assert cb.message.answer_audio.await_count == 2
    cb.answer.assert_called_once()


@pytest.mark.asyncio
async def test_pick_sound_reports_when_nothing_could_be_fetched(mock_bls):
    from app.bot.handlers.study import handle_study_callback
    mock_bls.get_session = AsyncMock(return_value=_session_with_sound_options("a/1.mp3"))
    mock_bls.get_sound = AsyncMock(return_value=None)
    cb = make_callback("study:lang1:pick_sound:0")

    with patch("app.bot.handlers.study.get_bls_client", return_value=mock_bls):
        await handle_study_callback(cb, make_state(), bls_user_id="user-1")

    cb.message.answer_audio.assert_not_awaited()
    cb.answer.assert_called_once_with("Звук недоступен", show_alert=True)


@pytest.mark.asyncio
async def test_pick_sound_survives_a_single_missing_variant(mock_bls):
    """Один вариант не отдался — остальные всё равно должны прозвучать."""
    from app.bot.handlers.study import handle_study_callback
    mock_bls.get_session = AsyncMock(
        return_value=_session_with_sound_options("a/1.mp3|a/2.mp3"))
    mock_bls.get_sound = AsyncMock(side_effect=[None, b"MP3"])
    cb = make_callback("study:lang1:pick_sound:0")

    with patch("app.bot.handlers.study.get_bls_client", return_value=mock_bls):
        await handle_study_callback(cb, make_state(), bls_user_id="user-1")

    assert cb.message.answer_audio.await_count == 1
    cb.answer.assert_called_once()

# ── упавший запрос не выдаётся за конец сессии ───────────────────────────────

@pytest.mark.asyncio
async def test_backend_failure_is_not_reported_as_session_completed(mock_bls):
    """
    Клиент возвращал `result.get("data") or {}`, поэтому упавший с 500 запрос был
    неотличим от «карточки больше нет», и человек получал поздравление
    «🎉 Все слова на сегодня изучены» из-за моргнувшего бэкенда — вместе с
    потерянным занятием.
    """
    from app.bot.handlers.study import handle_study_callback
    mock_bls.know_word = AsyncMock(return_value={"_failed": True, "_status": 500})
    cb = make_callback("study:lang1:know")

    with patch("app.bot.handlers.study.get_bls_client", return_value=mock_bls):
        await handle_study_callback(cb, make_state(), bls_user_id="user-1")

    cb.message.answer.assert_not_called()
    cb.answer.assert_called_once()
    assert cb.answer.call_args.kwargs.get("show_alert") is True
    assert "не ответил" in cb.answer.call_args.args[0]


@pytest.mark.asyncio
async def test_real_completion_still_congratulates(mock_bls):
    """Настоящее «слов больше нет» должно по-прежнему поздравлять."""
    from app.bot.handlers.study import handle_study_callback, COMPLETED_TEXT
    mock_bls.know_word = AsyncMock(return_value={"session_id": "sess-1", "card": None})
    cb = make_callback("study:lang1:know")

    with patch("app.bot.handlers.study.get_bls_client", return_value=mock_bls):
        await handle_study_callback(cb, make_state(), bls_user_id="user-1")

    cb.message.answer.assert_called_once()
    assert cb.message.answer.call_args.args[0] == COMPLETED_TEXT


@pytest.mark.asyncio
async def test_failed_next_batch_is_not_reported_as_completed(mock_bls):
    from app.bot.handlers.study import handle_study_callback
    mock_bls.rate_word = AsyncMock(return_value={"batch_exhausted": True})
    mock_bls.next_batch = AsyncMock(return_value={"_failed": True, "_status": 502})
    cb = make_callback("study:lang1:rate:know")

    with patch("app.bot.handlers.study.get_bls_client", return_value=mock_bls):
        await handle_study_callback(cb, make_state(), bls_user_id="user-1")

    cb.message.answer.assert_not_called()
    assert "не ответил" in cb.answer.call_args.args[0]


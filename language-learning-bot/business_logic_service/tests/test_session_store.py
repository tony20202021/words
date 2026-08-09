"""
Хранилище сессий в памяти: перезапуск занятия не должен копить мусор.

_sessions хранит сессию по её id, _session_index — id по паре (пользователь,
язык). При повторном start_session индекс перезаписывался, а прежний словарь
оставался в _sessions навсегда: end_session снимает только текущий id. Каждое
«начать заново» подвешивало батч слов и настройки до перезапуска процесса.
"""

import pytest

from app.services import session_service as ss
from tests.test_offline_bundle import make_mock_api, make_word


@pytest.fixture(autouse=True)
def clean_store():
    ss._sessions.clear()
    ss._session_index.clear()
    yield
    ss._sessions.clear()
    ss._session_index.clear()


async def _start(user="u1", lang="l1"):
    api = make_mock_api(words=[make_word(i) for i in range(1, 4)],
                        settings={"random_pick_mode": False})
    return await ss.start_session(user, lang, api)


@pytest.mark.asyncio
async def test_restarting_replaces_the_previous_session():
    for _ in range(5):
        await _start()
    assert len(ss._sessions) == 1, f"осиротевшие сессии: {len(ss._sessions)}"
    assert len(ss._session_index) == 1


@pytest.mark.asyncio
async def test_ending_a_session_leaves_the_store_empty():
    await _start()
    ss.end_session("u1", "l1")
    assert ss._sessions == {}
    assert ss._session_index == {}


@pytest.mark.asyncio
async def test_sessions_of_different_users_coexist():
    """Замена должна касаться только своей пары, а не чистить чужие сессии."""
    await _start("u1", "l1")
    await _start("u2", "l1")
    await _start("u1", "l2")
    assert len(ss._sessions) == 3

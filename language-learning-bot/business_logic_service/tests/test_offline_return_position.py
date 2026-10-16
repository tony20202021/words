"""
Вернувшись из офлайна, человек не должен попадать на пройденное слово.

Что случилось 16.10.2026, по журналу:

    20:28:45  слово 132 — «знаю», онлайн
              связь пропала; кнопку «дальше» нажать не успели
              офлайн человек прошёл ещё несколько слов
    20:29:25  пачка офлайновых результатов принесла слово 136
              GET /session вернул слово 132 — назад, на уже пройденное

Почему так выходило. Сессия стояла на слове 132: оценка записана
(word_processed=True), но шаг к следующему слову делает отдельное нажатие, и
его не случилось. Сдвиг сессии за офлайновые результаты шёл «пока текущее
слово есть среди отвеченных» — а 132 отвечали ОНЛАЙН, в пачке его нет, и цикл
останавливался на первом же шаге.

Правильно — довести такое слово до конца так же, как это сделала бы кнопка
«дальше», и только потом идти по офлайновым.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))

from app.services import session_service as svc  # noqa: E402


def _session(current_index: int, word_processed: bool, score_changed: bool = True):
    """Сессия на словах w1..w5, стоящая на current_index."""
    words = [{"_id": f"w{i}", "word_number": 130 + i} for i in range(1, 6)]
    return {
        "user_id": "u1", "language_id": "l1", "session_id": "s1",
        "words": words, "current_index": current_index,
        "total_words_processed": current_index,
        "word_processed": word_processed, "score_changed": score_changed,
        "show_answer": word_processed, "settings": {},
        "correct_count": 0, "incorrect_count": 0, "result_history": [],
        "last_activity_at": "2026-10-16T20:28:45",
    }


@pytest.fixture(autouse=True)
def _clean_sessions():
    svc._sessions.clear()
    svc._session_index.clear()
    yield
    svc._sessions.clear()
    svc._session_index.clear()


def _register(session):
    svc._sessions[session["session_id"]] = session
    svc._session_index[svc._session_key("u1", "l1")] = session["session_id"]


def test_the_word_answered_right_before_the_outage_is_not_shown_again():
    """Тот самый случай: «знаю» нажали, «дальше» не успели, связь пропала."""
    session = _session(current_index=1, word_processed=True)
    _register(session)

    # Офлайн человек прошёл следующие два слова.
    svc._advance_session_past("u1", "l1", [("w3", "know"), ("w4", "know")])

    assert session["current_index"] == 4, (
        "сессия вернулась на уже отвеченное слово — человек увидит его заново")
    # Слово, отвеченное онлайн, попало в историю ровно один раз.
    assert session["result_history"] == ["know", "know", "know"]


def test_an_unanswered_word_still_stops_the_move():
    """
    Сдвиг по-прежнему не перепрыгивает через НЕотвеченное слово.

    Это и была причина, по которой двигались не на N шагов: порядок в партии
    свой, и слепой сдвиг унёс бы человека мимо слова, которого он не видел.
    """
    session = _session(current_index=1, word_processed=False)
    _register(session)

    # w2 не отвечено, а w3 отвечено офлайн — дальше w2 идти нельзя.
    svc._advance_session_past("u1", "l1", [("w3", "know")])

    assert session["current_index"] == 1, "сессия перескочила через непройденное слово"
    assert session["result_history"] == []


def test_the_rating_of_the_carried_word_is_remembered():
    """«Не знаю» перед обрывом должно попасть в историю как «не знаю»."""
    session = _session(current_index=0, word_processed=True, score_changed=False)
    _register(session)

    svc._advance_session_past("u1", "l1", [("w2", "know")])

    assert session["result_history"] == ["dont_know", "know"]
    assert session["current_index"] == 2


def test_nothing_happens_without_offline_results():
    """Пустая пачка сессию не трогает — даже стоящую на отвеченном слове."""
    session = _session(current_index=2, word_processed=True)
    _register(session)

    svc._advance_session_past("u1", "l1", [])

    assert session["current_index"] == 2
    assert session["result_history"] == []

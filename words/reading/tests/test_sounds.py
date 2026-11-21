"""Озвучка предложений для чтения: имена файлов, готовые голоса, что доделать.

Владелец (21.11.2026): «пусть в базе будут сгенерированы все [голоса], но
каждый раз на телефон передаётся рандомно выбранный один». Значит, у
предложения в базе — список готовых файлов, а выбирает из него карточка.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sounds import ГОЛОСА, готовые, ключ, путь  # noqa: E402
from gen_reading_sounds import задания  # noqa: E402
from load_to_db import запись  # noqa: E402


def test_ключ_по_тексту_а_не_по_месту():
    """Имя файла переживает перестановку примеров и правку чужих: оно от
    самого текста. Лишние пробелы на имя не влияют, другой текст — другое имя."""
    assert ключ("אני רוצה את זה") == ключ("  אני  רוצה את זה ")
    assert ключ("אני רוצה את זה") != ключ("אני לא רוצה")
    assert len(ключ("Hello.")) == 16


def test_путь_рядом_со_звуками_слов():
    p = путь("he", "hila", "זה טוב")
    assert p == f"sounds/he/reading/hila/{ключ('זה טוב')}.mp3"


def test_голоса_как_у_слов_и_у_иврита_четвёртый_piper():
    """Три голоса — те же, что у слов. Четвёртый у иврита — Piper noa (владелец
    выбрал его 21.11.2026 по образцам: «Б комфортнее всего»)."""
    assert [г for г, _, _ in ГОЛОСА["he"]] == ["gtts", "hila", "avri", "noa"]
    assert [д for _, д, _ in ГОЛОСА["he"]] == ["gtts", "edge", "edge", "piper"]
    assert [г for г, _, _ in ГОЛОСА["en"]] == ["gtts", "voice1", "voice2"]


def test_готовые_только_существующие_и_непустые(tmp_path):
    текст = "זה טוב"
    (tmp_path / путь("he", "gtts", текст)).parent.mkdir(parents=True)
    (tmp_path / путь("he", "gtts", текст)).write_bytes(b"mp3")
    (tmp_path / путь("he", "hila", текст)).parent.mkdir(parents=True)
    (tmp_path / путь("he", "hila", текст)).write_bytes(b"")     # оборванный
    assert готовые("he", текст, корень=tmp_path) == [путь("he", "gtts", текст)]


def test_генератор_доделывает_только_недостающее(tmp_path):
    """Повторный запуск продолжает с места обрыва и дубли не делает."""
    готов = путь("he", "gtts", "זה טוב")
    (tmp_path / готов).parent.mkdir(parents=True)
    (tmp_path / готов).write_bytes(b"mp3")
    работы = задания("he", ["זה טוב", "זה טוב", "אני לא יודע"], корень=tmp_path)
    пары = [(т, г) for т, г, _, _ in работы]
    assert ("זה טוב", "gtts") not in пары
    assert ("זה טוב", "hila") in пары and ("זה טוב", "avri") in пары
    assert len([п for п in пары if п[0] == "אני לא יודע"]) == 3
    assert len(пары) == 5


def test_голос_piper_делает_свой_скрипт_а_не_этот(tmp_path):
    """Piper живёт в отдельном окружении (Python 3.12): этот генератор его
    файлы не заказывает, иначе ждал бы движок, которого у него нет."""
    работы = задания("he", ["זה טוב"], корень=tmp_path)
    assert "noa" not in [г for _, г, _, _ in работы]
    assert {д for _, _, д, _ in работы} == {"gtts", "edge"}


def test_загрузчик_кладёт_в_запись_готовые_файлы(tmp_path):
    текст = "אני לא יודע"
    for г in ("hila", "avri"):
        (tmp_path / путь("he", г, текст)).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / путь("he", г, текст)).write_bytes(b"mp3")
    з = запись({"text": текст, "ru": "Я не знаю.", "tr": "ʔaˈni lo joˈdea"}, "he",
               корень=tmp_path)
    assert з["text"] == текст and з["tr"] == "ʔaˈni lo joˈdea"
    assert з["sounds"] == [путь("he", "hila", текст), путь("he", "avri", текст)]


def test_без_озвучки_поле_пустое(tmp_path):
    з = запись({"text": "זה טוב", "ru": "Это хорошо."}, "he", корень=tmp_path)
    assert з["sounds"] == []


def test_можно_взять_не_все_голоса(tmp_path):
    """21.11.2026 Google начал отказывать gTTS посреди английского (2463 пустых
    файла из ~6250): генерацию продолжают без него, а его догоняют потом."""
    работы = задания("en", ["Hello."], корень=tmp_path, голоса={"voice1", "voice2"})
    assert sorted(г for _, г, _, _ in работы) == ["voice1", "voice2"]

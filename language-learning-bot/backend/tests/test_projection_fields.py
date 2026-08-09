"""
Поле, объявленное в модели, обязано доезжать через каждую проекцию.

Зачем этот тест
---------------
Самый дорогой класс дефектов в этом проекте — «данные посчитаны, но до
потребителя не доехали». Части речи и леммы были посчитаны для всех 9995 слов
иврита, лежали в Mongo, были объявлены в схеме — и всё равно приходили как None,
потому что пять аггрегационных стадий `$project` перечисляют поля поимённо и
новых там не было. Ни один тест этого не видел: значение поля никто не проверял,
а проверять его сквозным тестом дорого — нужна база.

Тест структурный. Он читает исходники репозиториев, находит стадии `$project`,
которые перечисляют поля слова, и требует, чтобы каждое поле модели там
присутствовало. Это ловит момент добавления поля в модель без добавления в
проекцию — то есть ровно ту ошибку, которая случилась.

Чего он не ловит: неверное ЗНАЧЕНИЕ поля и случай, когда поле не записано в
Mongo вовсе. Это дело сквозных проверок и скриптов синхронизации.
"""

import ast
import re
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
REPOS = BACKEND / "app" / "db" / "repositories"

# Поля, которых в проекциях быть не обязано.
#   language_id / word_number  — есть везде, но иногда под другим именем ($toString)
#   *_unit_count               — служебные счётчики, наружу не отдаются
#   created_at / updated_at    — не всякая выборка их берёт
EXEMPT = {
    "word_foreign_unit_count", "transcription_unit_count",
    "created_at", "updated_at", "language_id", "sound_file_path",
}


def word_model_fields() -> set[str]:
    """Поля WordBase — единственный список, от которого пляшут все остальные."""
    from app.api.models.word import WordBase
    return set(WordBase.model_fields) - EXEMPT


def projection_blocks(path: Path) -> list[tuple[int, set[str]]]:
    """
    Стадии $project, перечисляющие поля СЛОВА.

    Ищем текстом, а не разбором Python: стадии собираются как литералы внутри
    длинных конвейеров, и вытащить их через ast — больше кода, чем пользы.
    Отбираем только те блоки, где встречается word_foreign: остальные проекции
    (статистика, языки) к словам отношения не имеют.
    """
    src = path.read_text(encoding="utf-8")
    out = []
    for m in re.finditer(r'"\$project"\s*:\s*\{', src):
        depth, i = 1, m.end()
        while i < len(src) and depth:
            depth += {"{": 1, "}": -1}.get(src[i], 0)
            i += 1
        block = src[m.end():i]
        if "word_foreign" not in block:
            continue
        line = src[:m.start()].count("\n") + 1
        out.append((line, set(re.findall(r'"([a-z_]+)"\s*:', block))))
    return out


ALL_BLOCKS = [(p.name, line, fields)
              for p in sorted(REPOS.glob("*_repository.py"))
              for line, fields in projection_blocks(p)]


def test_word_projections_are_found_at_all():
    """Если проекции перестали находиться, тест обязан упасть, а не молча пройти."""
    assert len(ALL_BLOCKS) >= 5, (
        f"найдено {len(ALL_BLOCKS)} проекций слова, ожидалось не меньше пяти — "
        "либо их переписали, либо сломался поиск, и тест больше ничего не проверяет")


@pytest.mark.parametrize("name,line,fields", ALL_BLOCKS,
                         ids=[f"{n}:{l}" for n, l, _ in ALL_BLOCKS])
def test_projection_carries_every_model_field(name, line, fields):
    missing = word_model_fields() - fields
    assert not missing, (
        f"{name}:{line} — проекция вырезает поля модели: {sorted(missing)}. "
        f"Поле объявлено в WordBase, лежит в Mongo, но до ответа API не доедет. "
        f"Именно так part_of_speech и lemma приходили как None.")

"""Согласование счётчиков с числом в вебе.

Дефект «1 ошибок» был одинаковый в андроиде и в вебе — одна и та же склеенная
строка в двух клиентах. Нашёл его снимок экрана андроида, но чинить пришлось оба.
"""
import pytest

from app.templating import plural, templates


@pytest.mark.parametrize(
    "n,expected",
    [
        (0, "ошибок"),
        (1, "ошибка"),
        (2, "ошибки"),
        (4, "ошибки"),
        (5, "ошибок"),
        (11, "ошибок"),  # 11-14 не подчиняются последней цифре
        (12, "ошибок"),
        (14, "ошибок"),
        (21, "ошибка"),
        (22, "ошибки"),
        (111, "ошибок"),
    ],
)
def test_plural_agrees_with_the_number(n, expected):
    assert plural(n, "ошибка", "ошибки", "ошибок") == expected


def test_filter_is_registered_for_templates():
    # Фильтр может существовать и не быть подключённым — тогда шаблон упадёт
    # уже у пользователя.
    assert "plural" in templates.env.filters
    rendered = templates.env.from_string(
        "{{ n | plural('ошибка', 'ошибки', 'ошибок') }}"
    ).render(n=1)
    assert rendered == "ошибка"

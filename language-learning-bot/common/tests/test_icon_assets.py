"""
Иконка приложения: одна картинка в трёх местах — значок на телефоне, экран
входа, сайт.

Почему это вообще проверяется. Значок порождается скриптом
(scripts/make_icon.py), и ошибиться тут можно молча:

  • перерисовали знак крупнее — и телефон с круглыми значками срежет углы
    листа, но увидит это только тот, у кого такая прошивка;
  • забыли плотность — и на части телефонов значок станет мыльным;
  • адаптивный XML ссылается на слой, которого нет — сборка проходит, значок
    не рисуется;
  • поменяли имя файла фавикона — вкладка браузера просто останется пустой.

Ни одно из этих падений не видно в прогоне обычных тестов.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "android" / "app" / "src" / "main" / "res"
STATIC = ROOT / "web_frontend" / "app" / "static"
MANIFEST = ROOT / "android" / "app" / "src" / "main" / "AndroidManifest.xml"

ПЛОТНОСТИ = ("mdpi", "hdpi", "xhdpi", "xxhdpi", "xxxhdpi")
# Android показывает только центральные 72dp из 108dp — остальное обрезает
# производитель, кругом или квадратом со скруглением.
БЕЗОПАСНО = 72 / 108


def test_every_density_has_the_launcher_icon():
    """
    Без плотности Android берёт ближайшую и растягивает: значок становится
    мыльным ровно на тех телефонах, которых нет под рукой.
    """
    for плотность in ПЛОТНОСТИ:
        d = RES / f"mipmap-{плотность}"
        for имя in ("ic_launcher.png", "ic_launcher_round.png",
                    "ic_launcher_foreground.png", "ic_launcher_background.png"):
            assert (d / имя).exists(), f"нет {плотность}/{имя}"


def test_the_launcher_sizes_match_the_densities():
    """48dp значка — это 48 px на mdpi и 192 на xxxhdpi, а не одно и то же."""
    from PIL import Image
    ожидание = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}
    for плотность, px in ожидание.items():
        im = Image.open(RES / f"mipmap-{плотность}" / "ic_launcher.png")
        assert im.size == (px, px), f"{плотность}: {im.size}, ожидалось {px}×{px}"


def test_the_adaptive_icon_points_at_layers_that_exist():
    """Ссылка на несуществующий слой не ломает сборку — значок просто пустой."""
    for имя in ("ic_launcher", "ic_launcher_round"):
        xml = (RES / "mipmap-anydpi-v26" / f"{имя}.xml").read_text(encoding="utf-8")
        for слой in re.findall(r'@mipmap/(\w+)', xml):
            assert (RES / "mipmap-xxxhdpi" / f"{слой}.png").exists(), \
                f"{имя}.xml ссылается на @mipmap/{слой}, которого нет"


def test_the_glyph_stays_inside_the_safe_zone():
    """
    Главная проверка. Android обрезает значок как хочет: кругом, квадратом со
    скруглением, каплей. Гарантированно видна только центральная зона 72dp из
    108dp — всё, что дальше, у кого-то пропадёт.

    Углы листа и есть самые дальние точки знака, и именно их срезает круглая
    обрезка. Проверяем по непрозрачным точкам переднего слоя.
    """
    from PIL import Image
    import numpy as np

    fg = Image.open(RES / "mipmap-xxxhdpi" / "ic_launcher_foreground.png").convert("RGBA")
    alpha = np.asarray(fg)[..., 3]
    ys, xs = np.where(alpha > 16)
    assert len(xs), "передний слой пуст — знака на значке не будет"

    N = fg.width
    центр = (N - 1) / 2
    дальняя = (((xs - центр) ** 2 + (ys - центр) ** 2).max()) ** 0.5
    предел = N * БЕЗОПАСНО / 2
    assert дальняя <= предел, (
        f"знак выходит за безопасную зону: {дальняя:.0f} px при пределе "
        f"{предел:.0f} — на телефонах с круглыми значками ему срежет углы")


def test_the_manifest_declares_both_icons():
    """
    Без android:icon система ставит зелёного робота по умолчанию — ровно то,
    что было до 07.11.2026. roundIcon нужен отдельно: часть прошивок берёт
    только его.
    """
    xml = MANIFEST.read_text(encoding="utf-8")
    assert 'android:icon="@mipmap/ic_launcher"' in xml
    assert 'android:roundIcon="@mipmap/ic_launcher_round"' in xml


def test_the_login_screen_shows_the_same_picture():
    """
    На экране входа стояло эмодзи 📚: оно рисуется шрифтом телефона, выглядит
    по-разному на разных прошивках и к значку приложения отношения не имеет.
    """
    layout = (RES / "layout" / "activity_login.xml").read_text(encoding="utf-8")
    assert "@drawable/app_logo" in layout
    assert (RES / "drawable-nodpi" / "app_logo.png").exists()
    # Смотреть надо на ВИДИМЫЙ текст, а не на весь файл: в пояснении рядом
    # эмодзи упомянуто нарочно, и проверка на его присутствие в файле ловила
    # собственный комментарий.
    без_пояснений = re.sub(r"<!--.*?-->", "", layout, flags=re.S)
    assert "📚" not in без_пояснений, "эмодзи вернулось вместо значка"


def test_the_site_has_the_icon_and_asks_for_it():
    """Файл без ссылки на него и ссылка без файла одинаково дают пустую вкладку."""
    base = (ROOT / "web_frontend" / "app" / "templates" / "base.html").read_text(encoding="utf-8")
    for файл in ("favicon.ico", "icon-192.png", "apple-touch-icon.png"):
        assert (STATIC / файл).exists(), f"нет {файл}"
        assert файл in base, f"{файл} есть, но base.html на него не ссылается"

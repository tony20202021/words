#!/usr/bin/env python3
"""
Иконка приложения: аватарка бота, значок на телефоне и фавикон сайта — из
одного рисунка.

Зачем один источник
-------------------
Аватарку бота в телеграме, значок приложения на экране телефона и фавикон
сайта легко развести: три разных файла, нарисованных в разное время. Тогда
человек видит три разные картинки у одной и той же вещи. Здесь рисунок один,
а всё остальное из него порождается.

Что порождается
---------------
  avatar/           квадрат 640 для @BotFather и лист просмотра
  android res/      значок во всех плотностях, круглый вариант и адаптивный
                    (отдельно знак, отдельно фон — так требует Android 8+)
  web static/       фавиконы и apple-touch-icon

Про адаптивный значок. Android 8+ рисует значок из двух слоёв на холсте
108dp и обрезает его как хочет — кругом, квадратом со скруглением, каплей.
Гарантированно видна только центральная зона 72dp, то есть две трети. Поэтому
знак для переднего слоя уменьшается: иначе углы листа срежет на телефонах с
круглыми значками.

Про цвет. В общем списке чатов цвет и есть опознавательный знак, а соседние
боты заняли синий, красный и зелёный; фиолетовый владелец отклонил — путался
с синим. Отсюда янтарный.

Про размер знака. Дальняя точка знака держится около 77% радиуса. Сначала
было 88%, и владелец заметил: «в круге диагонали почти касаются края». Углы
листа и есть самые дальние точки — именно они задают предел.

Запуск:
    python scripts/make_icon.py                 # всё на свои места
    python scripts/make_icon.py --out /tmp/x    # никуда не ставить, сложить туда
    python scripts/make_icon.py --variant book  # другой знак
"""
import argparse
import math
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
ANDROID_RES = ROOT / "android" / "app" / "src" / "main" / "res"
WEB_STATIC = ROOT / "web_frontend" / "app" / "static"

K = 4
S = 640 * K
C = S / 2

ВЕРХ, НИЗ = (255, 186, 72), (198, 92, 8)
ТЕНЬ = (120, 50, 0)

# Плотности экрана Android: имя каталога -> множитель к 48dp значка.
ПЛОТНОСТИ = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}

# Доля холста 108dp, которая видна при любой обрезке: 72/108.
БЕЗОПАСНО = 72 / 108


# ── фон ──────────────────────────────────────────────────────────────────────

def фон() -> Image.Image:
    """Диагональный градиент с тонкими кольцами и мягким бликом."""
    v = Image.linear_gradient("L").resize((S, S))
    t = ImageChops.add(v, v.rotate(90), scale=2.0)
    img = Image.composite(Image.new("RGB", (S, S), НИЗ),
                          Image.new("RGB", (S, S), ВЕРХ), t)

    кольца = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(кольца)
    for r in (0.30, 0.47, 0.64, 0.82):
        R = r * C
        d.ellipse((C - R, C - R, C + R, C + R), outline=34, width=6 * K)
    img = Image.composite(Image.new("RGB", (S, S), "white"), img, кольца)

    блик = Image.new("L", (S, S), 0)
    bx, by, br = C * 0.62, C * 0.45, C * 0.55
    ImageDraw.Draw(блик).ellipse((bx - br, by - br, bx + br, by + br), fill=55)
    блик = блик.filter(ImageFilter.GaussianBlur(br * 0.45))
    return Image.composite(Image.new("RGB", (S, S), "white"), img, блик)


def маска(*многоугольники) -> Image.Image:
    m = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(m)
    for p in многоугольники:
        d.polygon(p, fill=255)
    return m


# ── знаки ────────────────────────────────────────────────────────────────────

def тетрадь(M=1.70):
    """
    Лист в линейку и карандаш наискось. Возвращает (слои, общая маска).

    Карандаш тёмный намеренно: в первом заходе он был янтарный, как фон, и на
    копии 54 px пропадал — читался лентой поперёк листа. Контраст даёт не фон,
    а белый лист под ним.

    Срезы корпуса идут строго поперёк карандаша. В первом заходе нормаль была
    взята к другой оси, и все срезы шли наискось — владелец заметил сразу.
    """
    л, п = C - 400 * M, C + 300 * M
    в, н = C - 450 * M, C + 420 * M
    лист = Image.new("L", (S, S), 0)
    ImageDraw.Draw(лист).rounded_rectangle((л, в, п, н), 60 * M, fill=255)

    угол = math.radians(58)
    ox, oy = math.cos(угол), math.sin(угол)
    вдоль = (-ox, oy)
    поперёк = (oy, ox)
    assert abs(вдоль[0] * поперёк[0] + вдоль[1] * поперёк[1]) < 1e-12, \
        "поперечник карандаша обязан быть перпендикулярен его оси"

    вx, вy = C + 330 * M, C - 430 * M

    def точка(в_, п_):
        return (вx + вдоль[0] * в_ + поперёк[0] * п_,
                вy + вдоль[1] * в_ + поперёк[1] * п_)

    ш = 96 * M
    корпус_до, дерево_до, грифель_до = 760 * M, 900 * M, 975 * M
    корпус = [точка(0, -ш), точка(0, ш), точка(корпус_до, ш), точка(корпус_до, -ш)]
    дерево = [точка(корпус_до, -ш), точка(корпус_до, ш),
              точка(дерево_до, ш * 0.34), точка(дерево_до, -ш * 0.34)]
    грифель = [точка(дерево_до, -ш * 0.34), точка(дерево_до, ш * 0.34),
               точка(грифель_до, 0)]
    резинка = [точка(-110 * M, -ш), точка(-110 * M, ш), точка(0, ш), точка(0, -ш)]

    строки = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(строки)
    for i in range(5):
        y = в + 140 * M + i * 135 * M
        d.rounded_rectangle((л + 85 * M, y, п - 110 * M, y + 46 * M), 23 * M, fill=255)

    слои = [
        (лист, (255, 255, 255)),
        (строки, (240, 199, 150)),
        (маска(резинка), (236, 140, 150)),
        (маска(корпус), (92, 52, 20)),
        (маска(дерево), (250, 226, 188)),
        (маска(грифель), (52, 46, 44)),
    ]
    общая = лист
    for м in (маска(корпус, дерево, грифель, резинка),):
        общая = ImageChops.lighter(общая, м)
    return слои, общая


def книга(M=1.55):
    """Раскрытый разворот: правая страница чуть темнее, иначе это не книга."""
    верх, низ = C - 300 * M, C + 250 * M
    край, корешок = 560 * M, 44 * M
    левая = [(C - край, верх + 120 * M), (C - корешок, верх),
             (C - корешок, низ), (C - край, низ + 60 * M)]
    правая = [(C + край, верх + 120 * M), (C + корешок, верх),
              (C + корешок, низ), (C + край, низ + 60 * M)]

    строки = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(строки)
    for i in range(4):
        y = верх + 150 * M + i * 115 * M
        d.rounded_rectangle((C - край + 150 * M, y, C - корешок - 90 * M,
                             y + 42 * M), 21 * M, fill=255)
        d.rounded_rectangle((C + корешок + 90 * M, y, C + край - 150 * M,
                             y + 42 * M), 21 * M, fill=255)

    слои = [
        (маска(правая), (246, 228, 200)),
        (маска(левая), (255, 255, 255)),
        (строки, (235, 190, 140)),
    ]
    return слои, ImageChops.lighter(маска(левая), маска(правая))


ЗНАКИ = {"notebook": тетрадь, "book": книга}


# ── сборка ───────────────────────────────────────────────────────────────────

def нарисовать(variant: str, с_фоном: bool = True) -> Image.Image:
    слои, общая = ЗНАКИ[variant]()
    если_тень = ImageChops.offset(общая, 10 * K, 12 * K).point(lambda v: int(v * 0.28))

    if с_фоном:
        img = фон().convert("RGBA")
        img = Image.composite(Image.new("RGBA", (S, S), ТЕНЬ + (255,)), img, если_тень)
    else:
        img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        цвет = Image.new("RGBA", (S, S), ТЕНЬ + (255,))
        img = Image.composite(цвет, img, если_тень)

    for м, цвет in слои:
        img = Image.composite(Image.new("RGBA", (S, S), цвет + (255,)), img, м)
    return img


def кругом(img: Image.Image) -> Image.Image:
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).ellipse((0, 0, img.size[0] - 1, img.size[1] - 1), fill=255)
    out = img.convert("RGBA").copy()
    out.putalpha(m)
    return out


def умень(img: Image.Image, size: int) -> Image.Image:
    return img.resize((size, size), Image.LANCZOS)


def записать(path: Path, img: Image.Image) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


АДАПТИВ = """<?xml version="1.0" encoding="utf-8"?>
<!--
    Значок для Android 8+. Система рисует его из двух слоёв на холсте 108dp и
    обрезает по вкусу производителя: кругом, квадратом со скруглением, каплей.
    Гарантированно видна только центральная зона 72dp — поэтому знак на
    переднем слое уменьшен, иначе углы листа срезало бы на круглых значках.
-->
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@mipmap/ic_launcher_background" />
    <foreground android:drawable="@mipmap/ic_launcher_foreground" />
</adaptive-icon>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--variant", default="notebook", choices=sorted(ЗНАКИ))
    ap.add_argument("--out", default="", help="сложить всё сюда, ничего не ставя")
    args = ap.parse_args()

    квадрат = нарисовать(args.variant, с_фоном=True)
    знак = нарисовать(args.variant, с_фоном=False)
    только_фон = фон().convert("RGBA")

    если = Path(args.out) if args.out else None
    res = (если / "res") if если else ANDROID_RES
    web = (если / "static") if если else WEB_STATIC
    avatar = (если / "avatar") if если else (ROOT / "docs" / "icon")

    # ── аватарка бота ───────────────────────────────────────────────────────
    записать(avatar / f"bot_avatar_{args.variant}.png", умень(квадрат, 640).convert("RGB"))

    # ── Android ─────────────────────────────────────────────────────────────
    for имя, k in ПЛОТНОСТИ.items():
        d = res / f"mipmap-{имя}"
        записать(d / "ic_launcher.png", умень(квадрат, round(48 * k)).convert("RGB"))
        записать(d / "ic_launcher_round.png", умень(кругом(квадрат), round(48 * k)))
        # Адаптивный: холст 108dp, знак внутри центральных 72dp.
        холст = round(108 * k)
        записать(d / "ic_launcher_background.png", умень(только_фон, холст).convert("RGB"))
        поле = Image.new("RGBA", (холст, холст), (0, 0, 0, 0))
        внутри = умень(знак, max(1, round(холст * БЕЗОПАСНО)))
        поле.paste(внутри, ((холст - внутри.width) // 2,) * 2, внутри)
        записать(d / "ic_launcher_foreground.png", поле)
    for имя in ("ic_launcher", "ic_launcher_round"):
        путь = res / "mipmap-anydpi-v26" / f"{имя}.xml"
        путь.parent.mkdir(parents=True, exist_ok=True)
        путь.write_text(АДАПТИВ, encoding="utf-8")
    # Для показа внутри приложения: круглая, не зависит от плотности.
    записать(res / "drawable-nodpi" / "app_logo.png", умень(кругом(квадрат), 192))

    # ── веб ─────────────────────────────────────────────────────────────────
    записать(web / "apple-touch-icon.png", умень(квадрат, 180).convert("RGB"))
    записать(web / "icon-192.png", умень(квадрат, 192).convert("RGB"))
    записать(web / "icon-512.png", умень(квадрат, 512).convert("RGB"))
    ico = web / "favicon.ico"
    ico.parent.mkdir(parents=True, exist_ok=True)
    умень(кругом(квадрат), 64).save(ico, sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])

    print(f"знак: {args.variant}")
    print(f"  android: {res}")
    print(f"  веб:     {web}")
    print(f"  аватар:  {avatar}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

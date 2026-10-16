"""
Бот обязан называть APK тем, что в APK, а не тем, что в common/version.py.

Что случилось 09.10.2026. Версию подняли пять раз подряд, а собранный APK в
раздачу не положили ни разу: копирование файла стояло отдельным пунктом в
документации. Бот и страница скачивания брали номер из version.py, байты —
из android/LangBot.apk. Человек видел «версия 4.11.0», а скачивал 4.6.5.

Шаг копирования теперь делает сборка (android/app/build.gradle), а это — вторая
опора: что бы ни лежало в LangBot.apk, названо оно будет своим именем.
"""
import re
import zipfile
from pathlib import Path

from app.bot.handlers import start


def _fake_apk(path: Path, version: str) -> Path:
    apk = path / "LangBot.apk"
    with zipfile.ZipFile(apk, "w") as z:
        z.writestr("AndroidManifest.xml", version.encode("utf-16-le"))
    return apk


def test_the_bot_reads_the_version_out_of_the_apk(tmp_path):
    from common.version import __version__
    apk = _fake_apk(tmp_path, "9.8.7")
    assert start.apk_version(apk) == "9.8.7"
    assert start.apk_version(apk) != __version__


def test_the_handler_names_the_file_after_the_apk_not_the_sources(tmp_path):
    """Имя файла и текст сообщения обязаны говорить одно и то же — про APK."""
    # Путь берём у самого модуля: каталог запуска у pytest бывает разный.
    source = Path(start.__file__).read_text(encoding="utf-8")
    body = source[source.index("async def cmd_android"):]
    body = body[:body.index("\nasync def ")]

    assert "apk_version(_APK_PATH)" in body, "версия берётся не из APK"
    assert "LangBot-v{version}.apk" in body, "имя файла собрано не из версии APK"
    assert not re.search(r"v\{__version__\}", body), (
        "в сообщении осталась версия исходников: она расходится с отдаваемым файлом")

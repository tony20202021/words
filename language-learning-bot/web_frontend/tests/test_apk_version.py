"""
The download filename must come from the APK bytes, not from common/version.py —
otherwise bumping the version without redeploying the APK serves a file named
after a build that does not exist. See commit 70de9f3 for the fallout.
"""
import zipfile
from pathlib import Path

from app.routers.info import apk_version


def _fake_apk(tmp_path: Path, version: str | None) -> Path:
    apk = tmp_path / "LangBot.apk"
    with zipfile.ZipFile(apk, "w") as z:
        if version is None:
            z.writestr("AndroidManifest.xml", b"\x00\x00")
        else:
            z.writestr("AndroidManifest.xml", version.encode("utf-16-le"))
    return apk


def test_reads_version_from_the_apk_not_from_version_py(tmp_path):
    from common.version import __version__
    apk = _fake_apk(tmp_path, "9.8.7")
    assert apk_version(apk) == "9.8.7"
    assert apk_version(apk) != __version__


def test_falls_back_to_version_py_when_the_apk_is_unreadable(tmp_path):
    from common.version import __version__
    broken = tmp_path / "broken.apk"
    broken.write_bytes(b"not a zip")
    assert apk_version(broken) == __version__


def test_falls_back_when_no_version_string_is_present(tmp_path):
    from common.version import __version__
    assert apk_version(_fake_apk(tmp_path, None)) == __version__


def test_falls_back_when_the_manifest_is_ambiguous(tmp_path):
    """Several version-like strings — refuse to guess, use the known value."""
    from common.version import __version__
    apk = _fake_apk(tmp_path, "1.2.3 and 4.5.6")
    assert apk_version(apk) == __version__

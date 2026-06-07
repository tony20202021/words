import sys
import io
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import Response

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from common.help_text import HELP_TEXT
from common.version import __version__

router = APIRouter(tags=["info"])


def _make_qr_png(data: str) -> bytes:
    import qrcode
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@router.get("/qr")
async def make_qr(url: str):
    """Generate a QR code PNG for the given URL."""
    png = _make_qr_png(url)
    return Response(content=png, media_type="image/png")


@router.get("/help")
async def get_help():
    return {"text": HELP_TEXT}


@router.get("/version")
async def get_version():
    parts = [int(x) for x in __version__.split(".")]
    version_code = parts[0] * 10000 + parts[1] * 100 + parts[2]
    return {"version": __version__, "version_code": version_code}

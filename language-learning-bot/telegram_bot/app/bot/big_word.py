"""Generate a big-word PNG image (word + transcription) for Telegram."""

import io
import sys
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
from common.utils.font_utils import get_font_manager

_WIDTH = 800
_HEIGHT = 750
_BG = (255, 255, 255)
_FG = (50, 50, 50)
_TRANS_FG = (100, 100, 100)
_WORD_MAX_SIZE = 480
_TRANS_MAX_SIZE = 160
_MARGIN = 20


async def generate_big_word_image(word: str, transcription: Optional[str] = None) -> bytes:
    """Return PNG bytes of a large word + optional transcription image."""
    fm = get_font_manager()
    available = _WIDTH - 2 * _MARGIN

    word_font, _, w_w, w_h, w_by = await fm.auto_fit_font_size(
        word, available, _HEIGHT // 2, _WORD_MAX_SIZE, 12
    )

    t_font = t_w = t_h = t_by = None
    trans_text = ""
    if transcription:
        trans_text = f"[{transcription}]"
        t_font, _, t_w, t_h, t_by = await fm.auto_fit_font_size(
            trans_text, available, _HEIGHT // 4, _TRANS_MAX_SIZE, 12
        )

    img = Image.new("RGB", (_WIDTH, _HEIGHT), _BG)
    draw = ImageDraw.Draw(img)

    free = _HEIGHT - w_h - (t_h or 0)
    top = free * 0.4

    draw.text(((_WIDTH - w_w) // 2, top - w_by), word, font=word_font, fill=_FG)

    if t_font and transcription:
        draw.text(
            ((_WIDTH - t_w) // 2, top + w_h + free * 0.4 - t_by),
            trans_text,
            font=t_font,
            fill=_TRANS_FG,
        )

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

"""Shared Jinja2Templates instance with app globals (version, etc.)."""
import os
import sys
from pathlib import Path
from fastapi.templating import Jinja2Templates

# Ensure common/ is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from common.version import __version__

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
templates.env.globals["app_version"] = __version__
templates.env.globals["telegram_bot_url"] = os.environ.get(
    "TELEGRAM_BOT_URL", "https://t.me/language_learning_words_bot"
)
templates.env.globals["web_url"] = os.environ.get(
    "WEB_URL", ""
)
templates.env.globals["bls_url"] = os.environ.get(
    "BLS_PUBLIC_URL", os.environ.get("BLS_URL", "http://localhost:8531")
)

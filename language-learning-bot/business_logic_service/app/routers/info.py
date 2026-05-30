import sys
from pathlib import Path
from fastapi import APIRouter

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from common.help_text import HELP_TEXT

router = APIRouter(tags=["info"])


@router.get("/help")
async def get_help():
    return {"text": HELP_TEXT}

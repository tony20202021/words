from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from app.bls_client import get_bls_client

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


def _require_user(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return None, RedirectResponse("/login", status_code=302)
    return user_id, None


@router.get("/languages")
async def language_list(request: Request):
    user_id, redirect = _require_user(request)
    if redirect:
        return redirect

    bls = get_bls_client()
    langs = await bls.get_languages()
    stats = {}
    for lang in langs:
        s = await bls.get_statistics(user_id, lang["id"])
        stats[lang["id"]] = s

    return templates.TemplateResponse("languages.html", {
        "request": request,
        "languages": langs,
        "stats": stats,
        "first_name": request.session.get("first_name", ""),
    })

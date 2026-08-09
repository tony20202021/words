from fastapi import APIRouter, Request
from app.access import require_user as _require_user
from app.stats import fetch_stats_for_languages
from app.templating import templates
from app.bls_client import get_bls_client

router = APIRouter()




@router.get("/languages")
async def language_list(request: Request):
    user_id, redirect = _require_user(request)
    if redirect:
        return redirect

    bls = get_bls_client()
    langs = await bls.get_languages()
    stats = await fetch_stats_for_languages(bls, user_id, langs)

    return templates.TemplateResponse("languages.html", {
        "request": request,
        "languages": langs,
        "stats": stats,
        "first_name": request.session.get("first_name", ""),
    })

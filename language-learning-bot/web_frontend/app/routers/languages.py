from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from app.access import require_user as _require_user
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

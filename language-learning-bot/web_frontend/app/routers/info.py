import sys
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, Response, FileResponse
from app.templating import templates
from app.bls_client import get_bls_client

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from common.help_text import HELP_TEXT
from common.chart_manifest import CHART_SECTIONS, CHART_CAPTIONS

_APK_PATH = Path(__file__).parent.parent.parent.parent / "android" / "LangBot.apk"

router = APIRouter()


def _require_user(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return None, RedirectResponse("/login", status_code=302)
    return user_id, None


@router.get("/download/android")
async def download_android():
    if not _APK_PATH.exists():
        return Response("APK не найден", status_code=404)
    from common.version import __version__
    return FileResponse(
        path=str(_APK_PATH),
        media_type="application/vnd.android.package-archive",
        filename=f"LangBot-v{__version__}.apk",
    )


@router.get("/help")
async def help_page(request: Request):
    user_id, redirect = _require_user(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("help.html", {"request": request, "help_text": HELP_TEXT})


@router.get("/stats")
async def stats_page(request: Request, lang_id: str = None):
    user_id, redirect = _require_user(request)
    if redirect:
        return redirect

    bls = get_bls_client()
    import asyncio as _asyncio
    languages = await bls.get_languages()

    async def _fetch(lang):
        s = await bls.get_statistics(user_id, lang["id"])
        return lang, s

    results = await _asyncio.gather(*[_fetch(lang) for lang in languages])
    stats_list = [
        {"language": lang, "stats": s}
        for lang, s in results
        if s.get("words_studied", 0) > 0 or s.get("total_words", 0) > 0
    ]

    return templates.TemplateResponse("stats.html", {
        "request": request,
        "stats_list": stats_list,
        "target_lang_id": lang_id,
        "chart_sections": CHART_SECTIONS,
        "chart_captions": CHART_CAPTIONS,
    })


@router.get("/stats/chart/{language_id}/{chart_name}")
async def stats_chart(language_id: str, chart_name: str, request: Request):
    user_id, redirect = _require_user(request)
    if redirect:
        return redirect
    bls = get_bls_client()
    data = await bls.get_chart(user_id, language_id, chart_name)
    if data is None:
        return Response(status_code=404)
    return Response(content=data, media_type="image/png")


@router.get("/stats/monthly-chart/{language_id}/{chart_name}")
async def stats_monthly_chart(language_id: str, chart_name: str, request: Request):
    user_id, redirect = _require_user(request)
    if redirect:
        return redirect
    bls = get_bls_client()
    data = await bls.get_monthly_chart(user_id, language_id, chart_name, show_all=True)
    if data is None:
        return Response(status_code=404)
    return Response(content=data, media_type="image/png")


@router.get("/qr")
async def qr_code(url: str):
    """Proxy: generate QR code via BLS and return PNG to browser."""
    bls = get_bls_client()
    import httpx
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{bls.base_url}/qr", params={"url": url})
        if resp.status_code == 200:
            return Response(content=resp.content, media_type="image/png")
    return Response(status_code=404)


@router.get("/stats/monthly-chart-recent/{language_id}/{chart_name}")
async def stats_monthly_chart_recent(language_id: str, chart_name: str, request: Request):
    user_id, redirect = _require_user(request)
    if redirect:
        return redirect
    bls = get_bls_client()
    data = await bls.get_monthly_chart(user_id, language_id, chart_name, show_all=False)
    if data is None:
        return Response(status_code=404)
    return Response(content=data, media_type="image/png")

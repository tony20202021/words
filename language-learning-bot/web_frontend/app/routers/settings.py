from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from app.templating import templates
from pathlib import Path
from app.bls_client import get_bls_client

router = APIRouter()

NUMERIC_LABELS = {
    "start_word":                  "Начальное слово",
    "reset_same_day_hours":        "Сброс сессии: перерыв за день (ч)",
    "reset_cross_midnight_hours":  "Сброс сессии: час после полуночи",
    "unknown_limit_new_words":     "Лимит неизвестных слов",
    "max_check_interval":          "Макс. интервал повторения (дни)",
    "quiz_options_count":          "Кол-во вариантов в режиме выбора",
}

SETTING_LABELS = {
    "skip_marked":                   "Пропускать исключённые слова",
    "show_skip_button":              "Показывать кнопку Пропускать",
    "use_check_date":                "Учитывать дату",
    "show_check_date":               "Показывать дату проверки",
    "show_hint_meaning":             "Ассоциация на русском",
    "show_hint_phoneticsound":       "Звучание по слогам",
    "show_hint_phoneticassociation": "Ассоциация звучания",
    "show_hint_writing":             "Ассоциация написания",
    "show_big":                      "Показывать крупное написание",
    "show_radicals":                 "Показывать радикалы",
    "show_references":               "Показывать ссылки",
    "show_tones":                    "Показывать тоны",
    "show_sounds":                   "Показывать звуки",
    "random_transcription":          "Дополнительно использовать транскрипцию",
    "random_sound":                  "Дополнительно использовать звук",
    "random_pick_mode":              "Режим выбора (pick mode)",
    "show_charts":                   "Показывать графики",
    "show_short_captions":           "Короткие подписи",
    "receive_messages":              "Получать сообщения",
    "show_debug":                    "Отладочная информация",
}


def _require_user(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return None, RedirectResponse("/login", status_code=302)
    return user_id, None


@router.get("/settings/{language_id}")
async def settings_page(request: Request, language_id: str):
    user_id, redirect = _require_user(request)
    if redirect:
        return redirect

    bls = get_bls_client()
    languages = await bls.get_languages()
    lang = next((l for l in languages if l["id"] == language_id), None)
    current = await bls.get_settings(user_id, language_id)

    settings_list = [
        {"key": k, "label": label, "value": current.get(k, False)}
        for k, label in SETTING_LABELS.items()
    ]
    numeric_list = [
        {"key": k, "label": label, "value": current.get(k, 0)}
        for k, label in NUMERIC_LABELS.items()
    ]

    return templates.TemplateResponse("settings.html", {
        "request": request,
        "language": lang,
        "language_id": language_id,
        "settings": settings_list,
        "numeric_settings": numeric_list,
    })


@router.post("/settings/{language_id}/toggle")
async def toggle_setting(request: Request, language_id: str, key: str = Form(...)):
    user_id, redirect = _require_user(request)
    if redirect:
        return redirect

    bls = get_bls_client()
    await bls.toggle_setting(user_id, language_id, key)
    return RedirectResponse(f"/settings/{language_id}", status_code=302)


@router.post("/settings/{language_id}/set")
async def set_numeric_setting(
    request: Request, language_id: str,
    key: str = Form(...), value: int = Form(...),
):
    user_id, redirect = _require_user(request)
    if redirect:
        return redirect
    if key not in NUMERIC_LABELS:
        return RedirectResponse(f"/settings/{language_id}", status_code=302)

    bls = get_bls_client()
    await bls.set_setting(user_id, language_id, key, value)
    return RedirectResponse(f"/settings/{language_id}", status_code=302)

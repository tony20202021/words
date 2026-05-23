from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from pathlib import Path
from app.bls_client import get_bls_client

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

HELP_TEXT = """📚 Справка по использованию бота

Этот бот поможет вам эффективно изучать иностранные слова с использованием системы интервального повторения.

🔹 Основные команды:
/start - Начать работу с ботом
/language - Выбрать язык для изучения
/study - Начать изучение слов
/settings - Настройки процесса обучения
/stats - Показать статистику
/hint - Информация о подсказках
/cancel - Отмена текущего действия

🔹 Процесс изучения:
1. Выберите язык командой /language
2. Настройте процесс обучения командой /settings
3. Начните изучение командой /study
4. Для каждого слова вы можете:
   • Придумывать и использовать свои собственные подсказки
   • Отметить слово как запомненое/неизвестное
   • Пропустить слово

🔹 Система интервального повторения:
• Если вы отметили слово как запомненое, его интервал повторения увеличивается в 2 раза
• Интервалы повторения: 1, 2, 4, 8, 16, 32 дня
• Если вы не знаете слово, интервал сбрасывается до 1 дня
• При просмотре подсказки интервал также сбрасывается

🔹 Система подсказок:
Подсказки придумываются самостоятельно самим пользователем.
• Значение - ассоциация для слова на русском
• Фонетическая ассоциация - связь с похожими по звучанию словами
• Фонетика - разбиение слова на слоги
• Написание - мнемонические приемы для запоминания
• В настройках можно индивидуально включать/отключать типы подсказок

Если у вас остались вопросы, обратитесь к администратору бота (@Anton_Mikhalev).

Вызвать главное меню и начать обучение - можно по команде /start

Более подробно узнать про подсказки - команда /hint"""


def _require_user(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return None, RedirectResponse("/login", status_code=302)
    return user_id, None


@router.get("/help")
async def help_page(request: Request):
    user_id, redirect = _require_user(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("help.html", {"request": request, "help_text": HELP_TEXT})


@router.get("/stats")
async def stats_page(request: Request):
    user_id, redirect = _require_user(request)
    if redirect:
        return redirect

    bls = get_bls_client()
    languages = await bls.get_languages()

    stats_list = []
    for lang in languages:
        s = await bls.get_statistics(user_id, lang["id"])
        if s.get("words_studied", 0) > 0 or s.get("total_words", 0) > 0:
            stats_list.append({
                "language": lang,
                "stats": s,
            })

    return templates.TemplateResponse("stats.html", {
        "request": request,
        "stats_list": stats_list,
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

"""
Вердикт «можно ли закрыть старые порты» должен опознавать людей, а не считать
обращения.

Почему это вообще проверяется. Скрипт решает, оборвать ли связь установленным
приложениям: адрес сервера лежит в их настройках, и закрытие порта выглядит
для человека как «нет сети». Ошибиться можно в обе стороны, и обе проверены
здесь:

  слишком строго — сканеры стучатся круглосуточно, и счёт запросов держал бы
                   порт открытым вечно;
  слишком мягко  — тишина на старом порту одинаково выглядит и когда все
                   перешли, и когда никто не заходил.

Скрипт лежит в deploy/ с расширением .sh, но это питон — грузим по пути.
"""
import importlib.util
from datetime import datetime
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "deploy" / "old_ports_usage.sh"


def load():
    spec = importlib.util.spec_from_loader(
        "old_ports_usage",
        importlib.machinery.SourceFileLoader("old_ports_usage", str(SCRIPT)))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


import importlib.machinery  # noqa: E402  (нужен для SourceFileLoader выше)

mod = load()


def line(port, path, status, ua, addr="1.2.3.4", method="GET"):
    return (f'{addr} - - [01/Nov/2026:10:00:00 +0100] port={port} '
            f'"{method} {path} HTTP/2.0" {status} 100 "-" "{ua}"')


SCANNER = line(8443, "/", 404, "Mozilla/5.0 zgrab/0.x")
APP = line(8443, "/session/682436f92da018cbec1b237a/6a5f9b89f97381939e0699fb",
           200, "okhttp/4.12.0")
APP_NEW = line(8543, "/session/682436f92da018cbec1b237a/6a5f9b89f97381939e0699fb",
               200, "okhttp/4.12.0")


def судить(*pairs, expect=()):
    """Строки -> (код возврата, вывод одной строкой)."""
    entries = [(mod.parse_line(text), service) for text, service in pairs]
    ports, _ = mod.analyse(entries)
    code, lines = mod.verdict(ports, expect)
    return code, "\n".join(lines)


# ── разбор строки ────────────────────────────────────────────────────────────

def test_a_line_is_parsed_into_port_path_status_and_agent():
    rec = mod.parse_line(APP)
    assert rec["port"] == 8443
    assert rec["status"] == 200
    assert rec["ua"] == "okhttp/4.12.0"
    assert rec["path"].startswith("/session/")


def test_a_missing_space_before_the_agent_does_not_lose_it():
    """В журнале попадаются строки без пробела перед User-Agent."""
    broken = ('1.2.3.4 - - [01/Nov/2026:10:00:00 +0100] port=8543 '
              '"GET /statistics/x HTTP/2.0" 200 25442 "-""okhttp/4.12.0"')
    assert mod.parse_line(broken)["ua"] == "okhttp/4.12.0"


def test_the_query_string_is_cut_off_from_the_path():
    """Одноразовые коды входа приходят в запросе — в разборе им делать нечего."""
    rec = mod.parse_line(line(8544, "/login?code=СЕКРЕТ", 200, "Mozilla/5.0"))
    assert rec["path"] == "/login"
    assert "СЕКРЕТ" not in rec["path"]


def test_the_user_is_read_out_of_the_path():
    """Кто приходил, видно прямо в пути: /session/<user_id>/<language_id>."""
    assert mod.user_of("/session/682436f92da018cbec1b237a/6a5f9b89f97381939e0699fb") \
        == "682436f92da018cbec1b237a"
    assert mod.user_of("/session/start") is None


# ── опознание ────────────────────────────────────────────────────────────────

def test_a_scanner_probing_a_foreign_path_is_noise():
    """
    Ровно то, что пришло на 8443 за сутки 31.10: GET /, /webui/, /favicon.ico,
    сплошь 404. Чужой путь плюс отказ сервера — терять было нечего.
    """
    for path in ("/", "/webui/", "/favicon.ico", "/.env"):
        rec = mod.parse_line(line(8443, path, 404, "Mozilla/5.0 zgrab/0.x"))
        assert mod.classify(rec, "bls") == "шум", path


def test_the_application_is_a_client_by_its_agent():
    assert mod.classify(mod.parse_line(APP), "bls") == "клиент"
    sound = line(8543, "/sounds/sounds/he/gtts/13.mp3", 200,
                 "stagefright/1.2 (Linux;Android 13)")
    assert mod.classify(mod.parse_line(sound), "bls") == "клиент"


def test_a_legitimate_404_from_our_own_route_is_still_a_client():
    """
    Приложение штатно получает 404: после DELETE сессии оно её же и запрашивает.
    Путь наш — значит это человек, а не сканер.
    """
    rec = mod.parse_line(line(8443, "/session/abc/def", 404, "okhttp/4.12.0"))
    assert mod.classify(rec, "bls") == "клиент"


def test_a_scanner_that_hits_a_real_route_is_still_not_a_person():
    """
    Случай из живого журнала, на котором первая версия этой правки и
    ошиблась. CensysInspect запросил /version — наш настоящий маршрут, ответ
    200 — и был засчитан клиентом. Сканер, попавший в настоящий путь,
    выглядит как человек, и порт остался бы закрыт навсегда.

    Сканеры представляются честно: прикидываются браузером, но не друг другом.
    """
    censys = line(8443, "/version", 200,
                  "Mozilla/5.0 (compatible; CensysInspect/1.1; +https://about.censys.io/)")
    assert mod.classify(mod.parse_line(censys), "bls") == "шум"

    palo = line(8443, "/v1/metadata", 404,
                "Hello from Palo Alto Networks, find out more about our scans")
    assert mod.classify(mod.parse_line(palo), "bls") == "шум"


def test_a_request_without_any_agent_is_a_machine():
    """
    Строка из живого журнала 01.11: GET / с «-» вместо User-Agent, адрес из
    сети Censys. Браузер шлёт агента всегда, приложение тоже — пустым
    приходит голый сокет. Без этого правила один такой запрос держал бы 8444
    открытым и требовал бы разбирательства каждый день.
    """
    assert mod.classify(mod.parse_line(line(8444, "/", 200, "-")), "web") == "шум"
    assert mod.classify(mod.parse_line(line(8443, "/version", 200, "")), "bls") == "шум"


def test_an_anonymous_request_to_a_real_route_is_not_decided_automatically():
    """
    Браузер на /login и сканер на /login выглядят одинаково: путь наш, ответа
    достаточно, а кто пришёл — не видно. Назвать такое клиентом значит
    держать порт вечно; назвать шумом — оборвать человека, который как раз
    входит в веб. Поэтому это отдельный разряд: закрывать не даёт, но
    показывается человеку, а не решается за него.
    """
    assert mod.classify(mod.parse_line(line(8444, "/login", 200, "Mozilla/5.0")),
                        "web") == "безличное"
    assert mod.classify(mod.parse_line(line(8444, "/", 200, "Mozilla/5.0")),
                        "web") == "безличное"


def test_a_user_id_in_the_path_identifies_a_person_whatever_the_agent():
    """Браузер веба ходит по тем же адресам с user_id — его видно и без UA."""
    rec = mod.parse_line(line(8544, "/statistics/682436f92da018cbec1b237a/x",
                              200, "Mozilla/5.0"))
    assert mod.classify(rec, "web") == "клиент"


def test_something_served_from_an_unknown_path_is_not_called_noise():
    """
    Сервер что-то ОТДАЛ по пути, которого мы не знаем. Назвать это шумом
    нельзя: неизвестное — не то же самое, что безвредное.
    """
    rec = mod.parse_line(line(8443, "/какой-то-новый-маршрут", 200, "Mozilla/5.0"))
    assert mod.classify(rec, "bls") == "непонятное"


# ── вердикт ──────────────────────────────────────────────────────────────────

def test_scanner_noise_alone_does_not_keep_the_port_open():
    """
    Главная ошибка прежней версии: она считала запросы и на девяти обращениях
    сканеров говорила «закрывать рано». Сказала бы и через год.
    """
    code, text = судить((SCANNER, "bls"), (APP_NEW, "bls"))
    assert code == 0, text
    assert "МОЖНО ЗАКРЫВАТЬ" in text


def test_one_live_client_on_an_old_port_blocks_the_closing():
    code, text = судить((APP, "bls"), (APP_NEW, "bls"))
    assert code == 1
    assert "ЗАКРЫВАТЬ РАНО" in text
    assert "682436f92da018cbec1b237a" in text, "не сказано, кого оборвём"


def test_silence_everywhere_is_not_permission_to_close():
    """
    Обратная ошибка, опаснее первой. На старом порту тихо — но и на новом
    никого: человек просто не открывал приложение, а его настройки ждут
    первого запуска. Разрешать по такому нельзя.
    """
    code, text = судить((SCANNER, "bls"))
    assert code == 1, text
    assert "ДАННЫХ НЕ ХВАТАЕТ" in text


def test_an_anonymous_request_on_an_old_port_blocks_the_closing():
    """Не «наверное, можно»: решать, оборвать ли человека, должен человек."""
    code, text = судить((line(8444, "/login", 200, "Mozilla/5.0"), "web"),
                        (APP_NEW, "bls"))
    assert code == 1, text
    assert "РАЗБИРАТЬСЯ" in text
    assert "/login" in text, "строку не показали — разбираться не с чем"


def test_an_unexplained_request_blocks_the_closing_and_is_shown(capsys):
    strange = line(8443, "/какой-то-новый-маршрут", 200, "Mozilla/5.0")
    code, text = судить((strange, "bls"), (APP_NEW, "bls"))
    assert code == 1
    assert "РАЗБИРАТЬСЯ" in text
    assert "новый-маршрут" in text, "строку не показали — разбираться не с чем"


# ── кого ещё не видели ───────────────────────────────────────────────────────

ДРУГОЙ = "68305de55de050c061888237"


def test_a_user_we_have_not_seen_yet_holds_the_port_open():
    """
    Самый дорогой случай. На старых портах чисто, на новом виден владелец —
    и соблазн закрыть велик. Но второй человек за это окно просто не
    заходил, и его приложение всё ещё держит старый адрес: перенос
    случается при первом запуске новой версии, а не при обновлении файла.

    В журнале «не заходил» и «перешёл» выглядят одинаково, поэтому различить
    их может только список ожидаемых.
    """
    code, text = судить((SCANNER, "bls"), (APP_NEW, "bls"),
                        expect=["682436f92da018cbec1b237a", ДРУГОЙ])
    assert code == 1, text
    assert "ЖДЁМ ЛЮДЕЙ" in text
    assert ДРУГОЙ in text, "не сказано, кого именно ждём"


def test_everyone_expected_has_moved_and_the_port_may_close():
    both = APP_NEW.replace("682436f92da018cbec1b237a", ДРУГОЙ)
    code, text = судить((SCANNER, "bls"), (APP_NEW, "bls"), (both, "bls"),
                        expect=["682436f92da018cbec1b237a", ДРУГОЙ])
    assert code == 0, text
    assert "МОЖНО ЗАКРЫВАТЬ" in text


def test_without_a_list_the_verdict_says_what_it_cannot_vouch_for():
    """
    Без --expect скрипт честно оговаривается, а не выдаёт «можно» за полную
    проверку: он ручается только за тех, кого застал.
    """
    code, text = судить((SCANNER, "bls"), (APP_NEW, "bls"))
    assert code == 0
    assert "ручаюсь только за тех, кого застал" in text
    assert "--expect" in text

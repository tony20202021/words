"""
Admin diagnostics handler.
Collects and displays system health: CPU, memory, disk, services, version.
"""

import asyncio
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

import psutil
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from app.utils.callback_constants import CallbackData
from app.bot.states.centralized_states import AdminStates
from app.utils.admin_utils import is_user_admin
from app.utils.logger import setup_logger

diagnostics_router = Router()
logger = setup_logger(__name__)

# When the bot process started
_BOT_START_TIME = time.monotonic()

# TCP/HTTP checks: (name, host, port, http_path_or_None)
_SERVICES = [
    ("MongoDB",               "localhost", 8527, None),
    ("Backend API",           "localhost", 8500,  "/api/health"),
    ("Writing Images Service","localhost", 8600,  "/health"),
]

# Systemd unit checks: (display_name, unit_name)
_SYSTEMD_SERVICES = [
    ("Frontend (бот)", "langbot-frontend.service"),
]


# ---------------------------------------------------------------------------
# System collectors
# ---------------------------------------------------------------------------

def _proc_label(p: psutil.Process) -> str:
    """Build a meaningful process label from its command line."""
    try:
        cmdline = p.cmdline()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return p.info.get("name", "?")[:30]

    if not cmdline:
        return p.info.get("name", "?")[:30]

    name = p.info.get("name", "")
    if name in ("python", "python3"):
        # Prefer --process-name=X (our own convention)
        for arg in cmdline:
            if arg.startswith("--process-name="):
                return arg[len("--process-name="):]
        # -m module
        if "-m" in cmdline:
            idx = cmdline.index("-m")
            if idx + 1 < len(cmdline):
                return f"-m {cmdline[idx + 1]}"
        # script.py
        for arg in cmdline[1:]:
            if arg.endswith(".py") and not arg.startswith("-"):
                return Path(arg).name

    # Generic: join first two tokens, trim to 30 chars
    label = " ".join(cmdline[:2])
    return label[:30]


def _format_bytes(n: int) -> str:
    for unit in ("Б", "КБ", "МБ", "ГБ", "ТБ"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} ПБ"


def _uptime_str(seconds: float) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}ч {m}м {s}с"
    return f"{m}м {s}с"


def _collect_memory() -> str:
    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()
    lines = [
        "🧠 <b>Память (RAM)</b>",
        f"  Всего:  {_format_bytes(vm.total)}",
        f"  Занято: {_format_bytes(vm.used)} ({vm.percent:.1f}%)",
        f"  Свободно: {_format_bytes(vm.available)}",
    ]
    if swap.total:
        lines.append(f"  Swap: {_format_bytes(swap.used)} / {_format_bytes(swap.total)} ({swap.percent:.1f}%)")

    # Top-5 by memory RSS
    procs = []
    for p in psutil.process_iter(["pid", "name", "memory_info"]):
        try:
            rss = p.info["memory_info"].rss
            procs.append((rss, p.info["pid"], _proc_label(p)))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    procs.sort(reverse=True)
    lines.append("  <i>Топ-5 по памяти:</i>")
    for rss, pid, label in procs[:5]:
        lines.append(f"    {pid:>6}  {_format_bytes(rss):>10}  {label}")
    return "\n".join(lines)


def _collect_cpu() -> str:
    cpu_pct = psutil.cpu_percent(interval=0.5)
    count = psutil.cpu_count(logical=True)
    lines = [
        "⚙️ <b>CPU</b>",
        f"  Загрузка: {cpu_pct:.1f}%  (ядер: {count})",
    ]

    # Top-5 by CPU (exclude idle sleep processes)
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent"]):
        try:
            if p.info["name"] == "sleep":
                continue
            procs.append((p.info["cpu_percent"], p.info["pid"], _proc_label(p)))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    procs.sort(reverse=True)
    lines.append("  <i>Топ-5 по CPU:</i>")
    for pct, pid, label in procs[:5]:
        lines.append(f"    {pid:>6}  {pct:>6.1f}%  {label}")
    return "\n".join(lines)


def _collect_disk() -> str:
    lines = ["💾 <b>Диски</b>"]
    skip_fs = {"tmpfs", "devtmpfs", "squashfs", "overlay", "proc", "sysfs",
               "devpts", "cgroup", "cgroup2", "pstore", "mqueue", "hugetlbfs",
               "vfat", "efivarfs"}
    skip_mounts = {"/boot/efi", "/boot"}
    seen: set = set()
    for part in psutil.disk_partitions(all=False):
        if part.fstype in skip_fs or part.mountpoint in seen or part.mountpoint in skip_mounts:
            continue
        try:
            u = psutil.disk_usage(part.mountpoint)
        except PermissionError:
            continue
        seen.add(part.mountpoint)
        bar_filled = int(u.percent / 10)
        bar = "█" * bar_filled + "░" * (10 - bar_filled)
        warn = " ⚠️" if u.percent >= 90 else ""
        lines.append(
            f"  {part.mountpoint}\n"
            f"    [{bar}] {u.percent:.0f}%{warn}\n"
            f"    {_format_bytes(u.used)} / {_format_bytes(u.total)}  (своб. {_format_bytes(u.free)})"
        )
    return "\n".join(lines)


async def _check_service(name: str, host: str, port: int, http_path) -> Tuple[str, str]:
    """Returns (status_emoji + name, latency_str)."""
    loop = asyncio.get_event_loop()
    start = loop.time()
    try:
        # TCP reachability
        future = loop.run_in_executor(
            None,
            lambda: socket.create_connection((host, port), timeout=2)
        )
        conn = await asyncio.wait_for(future, timeout=3)
        conn.close()
        latency = (loop.time() - start) * 1000

        status = f"🟢 {name}"
        detail = f"{latency:.0f} мс"

        if http_path:
            # Try HTTP health check
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"http://{host}:{port}{http_path}",
                        timeout=aiohttp.ClientTimeout(total=2)
                    ) as resp:
                        if resp.status == 200:
                            detail = f"{latency:.0f} мс  HTTP {resp.status}"
                        else:
                            status = f"🟡 {name}"
                            detail = f"HTTP {resp.status}"
            except Exception:
                status = f"🟡 {name}"
                detail = "порт открыт, HTTP недоступен"
    except Exception:
        status = f"🔴 {name}"
        detail = "недоступен"
    return status, detail


def _check_systemd(display_name: str, unit: str) -> Tuple[str, str]:
    try:
        result = subprocess.run(
            ["systemctl", "is-active", unit],
            capture_output=True, text=True, timeout=2
        )
        state = result.stdout.strip()
        if state == "active":
            return f"🟢 {display_name}", "active"
        return f"🔴 {display_name}", state
    except Exception:
        return f"🔴 {display_name}", "ошибка проверки"


async def _collect_services() -> str:
    lines = ["🔌 <b>Сервисы</b>"]
    tasks = [_check_service(*s) for s in _SERVICES]
    results = await asyncio.gather(*tasks)
    for status, detail in results:
        lines.append(f"  {status}  —  {detail}")
    for display_name, unit in _SYSTEMD_SERVICES:
        status, detail = await asyncio.to_thread(_check_systemd, display_name, unit)
        lines.append(f"  {status}  —  {detail}")
    return "\n".join(lines)


def _collect_config() -> str:
    try:
        import yaml
        root = Path(__file__).parents[5]

        def load(rel: str) -> dict:
            with open(root / rel) as f:
                return yaml.safe_load(f) or {}

        db   = load("backend/conf/config/database.yaml").get("mongodb", {})
        back = load("backend/conf/config/api.yaml")
        writ = load("writing_images_service/conf/config/api.yaml")
        fapi = load("frontend/conf/config/api.yaml")

        lines = ["🔧 <b>Конфигурация портов</b>"]
        lines.append(f"  MongoDB:                {db.get('host','localhost')}:{db.get('port','?')}")
        lines.append(f"  Backend API:            {back.get('host','?')}:{back.get('port','?')}{back.get('prefix','')}")
        lines.append(f"  Writing Images Service: {writ.get('host','?')}:{writ.get('port','?')}")
        lines.append(f"  Frontend → Backend:     {fapi.get('base_url','?')}")
        return "\n".join(lines)
    except Exception as e:
        return f"🔧 <b>Конфигурация портов</b>\n  Ошибка: {e}"


def _collect_version() -> str:
    try:
        root = Path(__file__).parents[6]
        sys.path.insert(0, str(root))
        from common.version import __version__
    except Exception:
        __version__ = "неизвестна"
    py = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    uptime = _uptime_str(time.monotonic() - _BOT_START_TIME)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"ℹ️ <b>Система</b>\n"
        f"  Версия проекта: <code>{__version__}</code>\n"
        f"  Python:  {py}\n"
        f"  Uptime бота: {uptime}\n"
        f"  Время:   {now}"
    )


# ---------------------------------------------------------------------------
# Keyboard
# ---------------------------------------------------------------------------

def get_diagnostics_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔄 Обновить", callback_data=CallbackData.ADMIN_DIAGNOSTICS_REFRESH),
        InlineKeyboardButton(text="⬅️ Назад", callback_data=CallbackData.BACK_TO_ADMIN),
    ]])


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

async def _build_report() -> str:
    sections = await asyncio.gather(
        asyncio.to_thread(_collect_version),
        asyncio.to_thread(_collect_config),
        asyncio.to_thread(_collect_cpu),
        asyncio.to_thread(_collect_memory),
        asyncio.to_thread(_collect_disk),
        _collect_services(),
    )
    return "\n\n".join(sections)


@diagnostics_router.callback_query(F.data == CallbackData.ADMIN_DIAGNOSTICS)
async def show_diagnostics(callback: CallbackQuery, state: FSMContext):
    if not await is_user_admin(callback, state):
        await callback.answer("Нет доступа.", show_alert=True)
        return

    await callback.answer()
    await callback.message.edit_text(
        "⏳ Собираю данные...",
        reply_markup=None,
    )
    await state.set_state(AdminStates.viewing_diagnostics)

    report = await _build_report()
    await callback.message.edit_text(
        report,
        parse_mode="HTML",
        reply_markup=get_diagnostics_keyboard(),
    )


@diagnostics_router.callback_query(F.data == CallbackData.ADMIN_DIAGNOSTICS_REFRESH)
async def refresh_diagnostics(callback: CallbackQuery, state: FSMContext):
    if not await is_user_admin(callback, state):
        await callback.answer("Нет доступа.", show_alert=True)
        return

    await callback.answer("Обновляю...")
    report = await _build_report()
    try:
        await callback.message.edit_text(
            report,
            parse_mode="HTML",
            reply_markup=get_diagnostics_keyboard(),
        )
    except Exception:
        # Message unchanged — no-op
        pass

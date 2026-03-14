import os
from pathlib import Path

CONFIG_DIR = Path(__file__).parent


def _read_file(name: str) -> str:
    """Читает файл конфига; возвращает пустую строку если не найден."""
    p = CONFIG_DIR / name
    return p.read_text(encoding="utf-8").strip() if p.exists() else ""


def get_token() -> str:
    return os.environ.get("BOT_TOKEN") or _read_file("token.txt")


def get_admins() -> set:
    """Возвращает множество из numeric ID (int) и username'ов без @ (str)."""
    raw = os.environ.get("ADMINS") or _read_file("admins.txt")
    # Поддерживаем как запятые (env), так и переносы строк (файл)
    result = set()
    for v in raw.replace(",", "\n").splitlines():
        v = v.strip().lstrip("@")
        if not v:
            continue
        if v.isdigit():
            result.add(int(v))
        else:
            result.add(v.lower())
    return result


def get_notify_group_id() -> int:
    """Группа для уведомлений о заказах."""
    return int(os.environ.get("NOTIFY_GROUP_ID") or _read_file("group_notify.txt"))


def get_admin_group_id() -> int:
    """Группа для команд администраторов."""
    return int(os.environ.get("ADMIN_GROUP_ID") or _read_file("group_admin.txt"))

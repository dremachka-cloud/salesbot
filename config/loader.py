from pathlib import Path

CONFIG_DIR = Path(__file__).parent


def get_token() -> str:
    return (CONFIG_DIR / "token.txt").read_text(encoding="utf-8").strip()


def get_admins() -> set:
    """Возвращает множество из numeric ID (int) и username'ов без @ (str)."""
    text = (CONFIG_DIR / "admins.txt").read_text(encoding="utf-8")
    result = set()
    for line in text.splitlines():
        v = line.strip().lstrip("@")
        if not v:
            continue
        if v.isdigit():
            result.add(int(v))
        else:
            result.add(v.lower())
    return result


def get_notify_group_id() -> int:
    """Группа для уведомлений о заказах."""
    return int((CONFIG_DIR / "group_notify.txt").read_text(encoding="utf-8").strip())


def get_admin_group_id() -> int:
    """Группа для команд администраторов."""
    return int((CONFIG_DIR / "group_admin.txt").read_text(encoding="utf-8").strip())

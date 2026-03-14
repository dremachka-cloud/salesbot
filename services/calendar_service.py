import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

CALENDAR_FILE = Path(__file__).parent.parent / "data" / "calendar.json"

# Дни недели для выдачи: 2=среда, 5=суббота (понедельник=0)
DEFAULT_WEEKDAYS = {2, 5}
DEADLINE_DAYS_BEFORE = 2
DEADLINE_HOUR = 20

MONTHS_RU = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
}
WEEKDAYS_RU = {
    0: "пн", 1: "вт", 2: "ср",
    3: "чт", 4: "пт", 5: "сб", 6: "вс",
}


def _parse(date_str: str) -> date:
    return datetime.strptime(date_str, "%Y%m%d").date()


def _fmt(d: date) -> str:
    return d.strftime("%Y%m%d")


def generate_dates(weeks_ahead: int = 4) -> list[str]:
    today = date.today()
    end = today + timedelta(weeks=weeks_ahead)
    result = []
    current = today
    while current <= end:
        if current.weekday() in DEFAULT_WEEKDAYS:
            result.append(_fmt(current))
        current += timedelta(days=1)
    return result


def load_calendar() -> list[str]:
    if not CALENDAR_FILE.exists():
        return []
    with open(CALENDAR_FILE, encoding="utf-8") as f:
        data = json.load(f)
    return sorted(set(data))


def save_calendar(dates: list[str]) -> None:
    with open(CALENDAR_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(set(dates)), f, ensure_ascii=False, indent=2)


def refresh_calendar(weeks_ahead: int = 4) -> None:
    existing = set(load_calendar())
    generated = set(generate_dates(weeks_ahead))
    merged = sorted(existing | generated)
    save_calendar(merged)


def add_date(date_str: str) -> None:
    try:
        _parse(date_str)
    except ValueError:
        raise ValueError(f"Неверный формат даты: '{date_str}'. Используйте YYYYMMDD")
    dates = load_calendar()
    if date_str in dates:
        raise ValueError(f"Дата {date_str} уже есть в календаре")
    dates.append(date_str)
    save_calendar(dates)


def remove_date(date_str: str) -> None:
    dates = load_calendar()
    if date_str not in dates:
        raise ValueError(f"Дата {date_str} не найдена в календаре")
    dates.remove(date_str)
    save_calendar(dates)


def _deadline_passed(date_str: str, now: Optional[datetime] = None) -> bool:
    """Возвращает True если дедлайн приёма заказов уже прошёл."""
    if now is None:
        now = datetime.now()
    delivery = _parse(date_str)
    deadline = datetime(
        delivery.year, delivery.month, delivery.day,
        DEADLINE_HOUR, 0, 0
    ) - timedelta(days=DEADLINE_DAYS_BEFORE)
    return now >= deadline


def get_upcoming_dates(n: int = 3) -> list[str]:
    """Даты выдачи начиная с сегодня (без фильтрации по дедлайну).
    Используется для /bake и /orders — заказы уже приняты, дедлайн неважен."""
    today = date.today().strftime("%Y%m%d")
    dates = [d for d in load_calendar() if d >= today]
    return dates[:n]


def get_available_dates(n: int = 3, now: Optional[datetime] = None) -> list[str]:
    dates = load_calendar()
    available = [d for d in dates if not _deadline_passed(d, now)]
    return available[:n]


def format_date(date_str: str) -> str:
    d = _parse(date_str)
    weekday = WEEKDAYS_RU[d.weekday()]
    return f"{d.day} {MONTHS_RU[d.month]} ({weekday})"


def format_deadline(date_str: str) -> str:
    """Возвращает строку вида 'до 20:00 16.03 (пн)'."""
    delivery = _parse(date_str)
    deadline_dt = datetime(
        delivery.year, delivery.month, delivery.day,
        DEADLINE_HOUR, 0, 0
    ) - timedelta(days=DEADLINE_DAYS_BEFORE)
    d = deadline_dt.date()
    return f"до 20:00 {d.day:02d}.{d.month:02d} ({WEEKDAYS_RU[d.weekday()]})"

import json
import pytest
from datetime import datetime, date, timedelta
from pathlib import Path

import services.calendar_service as cs


@pytest.fixture(autouse=True)
def tmp_calendar_file(tmp_path, monkeypatch):
    cal_file = tmp_path / "calendar.json"
    cal_file.write_text("[]")
    monkeypatch.setattr(cs, "CALENDAR_FILE", cal_file)
    return cal_file


def test_generate_dates_contains_wed_and_sat():
    dates = cs.generate_dates(weeks_ahead=2)
    parsed = [datetime.strptime(d, "%Y%m%d").date() for d in dates]
    weekdays = {d.weekday() for d in parsed}
    assert weekdays <= {2, 5}  # только среды и субботы


def test_generate_dates_count():
    dates = cs.generate_dates(weeks_ahead=4)
    # За 4 недели (~28 дней) должно быть ~8 дат
    assert 7 <= len(dates) <= 9


def test_load_empty_calendar():
    assert cs.load_calendar() == []


def test_save_and_load_roundtrip():
    dates = ["20260318", "20260321"]
    cs.save_calendar(dates)
    assert cs.load_calendar() == sorted(dates)


def test_save_deduplicates():
    cs.save_calendar(["20260318", "20260318"])
    assert cs.load_calendar().count("20260318") == 1


def test_refresh_calendar_adds_dates():
    cs.refresh_calendar(weeks_ahead=2)
    assert len(cs.load_calendar()) > 0


def test_refresh_calendar_no_duplicates():
    cs.refresh_calendar()
    cs.refresh_calendar()
    dates = cs.load_calendar()
    assert len(dates) == len(set(dates))


def test_add_date():
    cs.add_date("20261231")
    assert "20261231" in cs.load_calendar()


def test_add_date_invalid_format():
    with pytest.raises(ValueError, match="формат"):
        cs.add_date("31122026")


def test_add_date_duplicate():
    cs.add_date("20261231")
    with pytest.raises(ValueError, match="уже есть"):
        cs.add_date("20261231")


def test_remove_date():
    cs.add_date("20261231")
    cs.remove_date("20261231")
    assert "20261231" not in cs.load_calendar()


def test_remove_date_not_found():
    with pytest.raises(ValueError, match="не найдена"):
        cs.remove_date("20261231")


# --- Дедлайн ---

def test_deadline_passed_before_deadline():
    # Дата выдачи — через 3 дня, дедлайн ещё не прошёл
    delivery = date.today() + timedelta(days=3)
    date_str = delivery.strftime("%Y%m%d")
    now = datetime.now().replace(hour=10)  # 10:00
    assert not cs._deadline_passed(date_str, now)


def test_deadline_passed_after_deadline():
    # Дата выдачи — завтра, дедлайн (вчера 20:00) уже прошёл
    delivery = date.today() + timedelta(days=1)
    date_str = delivery.strftime("%Y%m%d")
    now = datetime.now()
    assert cs._deadline_passed(date_str, now)


def test_deadline_passed_exactly_at_deadline():
    delivery = date.today() + timedelta(days=2)
    date_str = delivery.strftime("%Y%m%d")
    # Ровно в момент дедлайна — уже закрыт
    deadline_now = datetime(
        date.today().year, date.today().month, date.today().day, 20, 0, 0
    )
    assert cs._deadline_passed(date_str, deadline_now)


def test_get_available_dates_filters_past_deadline():
    # Добавляем дату с прошедшим дедлайном (завтра) и будущую (через 5 дней)
    tomorrow = (date.today() + timedelta(days=1)).strftime("%Y%m%d")
    future = (date.today() + timedelta(days=5)).strftime("%Y%m%d")
    cs.save_calendar([tomorrow, future])
    now = datetime.now().replace(hour=21)  # после 20:00
    available = cs.get_available_dates(3, now=now)
    assert tomorrow not in available
    assert future in available


def test_get_available_dates_limits_to_n():
    # Создаём 5 дат далеко в будущем
    dates = [(date.today() + timedelta(days=10 + i)).strftime("%Y%m%d") for i in range(5)]
    cs.save_calendar(dates)
    available = cs.get_available_dates(3)
    assert len(available) <= 3


# --- Форматирование ---

def test_format_date_wednesday():
    # Найдём ближайшую среду
    d = date.today()
    while d.weekday() != 2:
        d += timedelta(days=1)
    result = cs.format_date(d.strftime("%Y%m%d"))
    assert "среда" in result
    assert str(d.day) in result


def test_format_date_saturday():
    d = date.today()
    while d.weekday() != 5:
        d += timedelta(days=1)
    result = cs.format_date(d.strftime("%Y%m%d"))
    assert "суббота" in result

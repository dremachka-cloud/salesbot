import csv
import json
import pytest
from pathlib import Path
from datetime import date

import services.order_service as os_
import services.bread_service as bs
import services.calendar_service as cs


SAMPLE_CART = {"Бородинский": 2, "Ржаной": 1}
DELIVERY_DATE = "20260318"


@pytest.fixture(autouse=True)
def tmp_files(tmp_path, monkeypatch):
    # orders.json
    orders_file = tmp_path / "orders.json"
    orders_file.write_text("[]")
    monkeypatch.setattr(os_, "ORDERS_FILE", orders_file)

    # bread.csv
    bread_file = tmp_path / "bread.csv"
    with open(bread_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Бородинский", 150])
        writer.writerow(["Ржаной", 120])
    monkeypatch.setattr(bs, "BREAD_FILE", bread_file)

    # calendar.json
    cal_file = tmp_path / "calendar.json"
    cal_file.write_text(json.dumps([DELIVERY_DATE]))
    monkeypatch.setattr(cs, "CALENDAR_FILE", cal_file)


def test_create_order_returns_dict():
    order = os_.create_order(123, "testuser", DELIVERY_DATE, SAMPLE_CART)
    assert order["user_id"] == 123
    assert order["date"] == DELIVERY_DATE
    assert order["total"] == 150 * 2 + 120 * 1


def test_create_order_saves_to_file():
    os_.create_order(123, None, DELIVERY_DATE, SAMPLE_CART)
    orders = os_.load_orders()
    assert len(orders) == 1


def test_create_multiple_orders():
    os_.create_order(1, "a", DELIVERY_DATE, {"Бородинский": 1})
    os_.create_order(2, "b", DELIVERY_DATE, {"Ржаной": 2})
    assert len(os_.load_orders()) == 2


def test_get_orders_for_date():
    os_.create_order(1, None, DELIVERY_DATE, SAMPLE_CART)
    os_.create_order(2, None, "20260321", {"Ржаной": 1})
    result = os_.get_orders_for_date(DELIVERY_DATE)
    assert len(result) == 1
    assert result[0]["user_id"] == 1


def test_get_orders_for_today():
    order = os_.create_order(1, None, DELIVERY_DATE, SAMPLE_CART)
    # created_at начинается с сегодняшней даты
    today = date.today()
    today_str = f"{today.year}-{today.month:02d}-{today.day:02d}"
    assert order["created_at"].startswith(today_str)
    result = os_.get_orders_for_today()
    assert len(result) == 1


def test_format_order_notification_with_username():
    order = os_.create_order(123, "baker_fan", DELIVERY_DATE, SAMPLE_CART)
    text = os_.format_order_notification(order)
    assert "Новый заказ" in text
    assert "@baker_fan" in text
    assert "Бородинский" in text
    assert "Итого" in text


def test_format_order_notification_no_username():
    order = os_.create_order(123, None, DELIVERY_DATE, SAMPLE_CART)
    text = os_.format_order_notification(order)
    assert "ID: 123" in text


def test_format_daily_summary_empty():
    assert os_.format_daily_summary([]) == ""


def test_format_daily_summary_groups_by_date():
    o1 = os_.create_order(1, None, DELIVERY_DATE, {"Бородинский": 1})
    o2 = os_.create_order(2, None, DELIVERY_DATE, {"Бородинский": 2})
    text = os_.format_daily_summary([o1, o2])
    assert "Бородинский × 3" in text
    assert "Итог заказов" in text


def test_order_has_unique_ids():
    o1 = os_.create_order(1, None, DELIVERY_DATE, SAMPLE_CART)
    o2 = os_.create_order(2, None, DELIVERY_DATE, SAMPLE_CART)
    assert o1["order_id"] != o2["order_id"]

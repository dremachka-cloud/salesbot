import json
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from services.calendar_service import format_date

ORDERS_FILE = Path(__file__).parent.parent / "data" / "orders.json"


def load_orders() -> list[dict]:
    if not ORDERS_FILE.exists():
        return []
    with open(ORDERS_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_orders(orders: list[dict]) -> None:
    with open(ORDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)


def create_order(
    user_id: int,
    username: Optional[str],
    delivery_date: str,
    items: dict,
) -> dict:
    """
    items: {название: количество}
    Возвращает созданный объект заказа.
    """
    bread_items = _build_items(items)
    total = sum(i["price"] * i["qty"] for i in bread_items)
    order = {
        "order_id": str(uuid.uuid4()),
        "user_id": user_id,
        "username": username,
        "date": delivery_date,
        "items": bread_items,
        "total": total,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    orders = load_orders()
    orders.append(order)
    save_orders(orders)
    return order


def _build_items(cart: dict) -> list:
    """Конвертирует корзину {name: qty} в список с ценами из bread_service."""
    from services.bread_service import load_bread
    price_map = {b["name"]: b["price"] for b in load_bread()}
    result = []
    for name, qty in cart.items():
        if qty > 0:
            result.append({
                "name": name,
                "price": price_map.get(name, 0),
                "qty": qty,
            })
    return result


def get_orders_for_date(date_str: str) -> list[dict]:
    return [o for o in load_orders() if o["date"] == date_str]


def get_orders_for_today() -> list[dict]:
    today = date.today().strftime("%Y%m%d")
    created_today = []
    for o in load_orders():
        created = o.get("created_at", "")
        if created.startswith(today[:4] + "-" + today[4:6] + "-" + today[6:8]):
            created_today.append(o)
    return created_today


def format_order_notification(order: dict) -> str:
    user_info = f"@{order['username']}" if order.get("username") else f"ID: {order['user_id']}"
    lines = [
        "📦 <b>Новый заказ</b>",
        f"Дата выдачи: {format_date(order['date'])}",
        f"Пользователь: {user_info} (ID: {order['user_id']})",
        "",
    ]
    for item in order["items"]:
        lines.append(f"{item['name']} × {item['qty']} — {item['price'] * item['qty']} ₽")
    lines.append("──────────────")
    lines.append(f"Итого: {order['total']} ₽")
    return "\n".join(lines)


def format_daily_summary(orders: list[dict]) -> str:
    if not orders:
        return ""

    # Группируем по дате выдачи
    by_date: dict[str, list[dict]] = {}
    for o in orders:
        by_date.setdefault(o["date"], []).append(o)

    lines = ["📊 <b>Итог заказов за сегодня</b>", ""]
    for d_str in sorted(by_date):
        day_orders = by_date[d_str]
        lines.append(f"<b>{format_date(d_str)}</b> — {len(day_orders)} заказ(ов)")

        # Суммируем позиции
        totals: dict[str, dict] = {}
        for o in day_orders:
            for item in o["items"]:
                name = item["name"]
                if name not in totals:
                    totals[name] = {"price": item["price"], "qty": 0}
                totals[name]["qty"] += item["qty"]

        for name, data in totals.items():
            lines.append(f"  • {name} × {data['qty']} — {data['price'] * data['qty']} ₽")
        lines.append("")

    return "\n".join(lines).rstrip()


def cleanup_old_orders() -> int:
    """Удаляет заказы, дата выдачи которых уже прошла. Возвращает кол-во удалённых."""
    today = date.today().strftime("%Y%m%d")
    orders = load_orders()
    fresh = [o for o in orders if o.get("date", "99999999") >= today]
    removed = len(orders) - len(fresh)
    if removed:
        save_orders(fresh)
    return removed

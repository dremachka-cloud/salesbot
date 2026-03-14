import csv
import os
from pathlib import Path

BREAD_FILE = Path(__file__).parent.parent / "data" / "bread.csv"


def load_bread() -> list[dict]:
    if not BREAD_FILE.exists():
        return []
    items = []
    with open(BREAD_FILE, newline="", encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) >= 2:
                name = row[0].strip()
                try:
                    price = int(row[1].strip())
                except ValueError:
                    continue
                items.append({"name": name, "price": price})
    return items


def save_bread(items: list[dict]) -> None:
    with open(BREAD_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for item in items:
            writer.writerow([item["name"], item["price"]])


def add_bread(name: str, price: int) -> None:
    name = name.strip()
    items = load_bread()
    if any(i["name"].lower() == name.lower() for i in items):
        raise ValueError(f"Хлеб '{name}' уже есть в ассортименте")
    items.append({"name": name, "price": price})
    save_bread(items)


def remove_bread(name: str) -> None:
    name = name.strip()
    items = load_bread()
    new_items = [i for i in items if i["name"].lower() != name.lower()]
    if len(new_items) == len(items):
        raise ValueError(f"Хлеб '{name}' не найден в ассортименте")
    save_bread(new_items)


def list_bread() -> str:
    items = load_bread()
    if not items:
        return "Ассортимент пуст"
    lines = ["<b>Текущий ассортимент:</b>"]
    for item in items:
        lines.append(f"• {item['name']} — {item['price']} ₽")
    return "\n".join(lines)

import csv
import pytest
from pathlib import Path
from unittest.mock import patch

import services.bread_service as bs

SAMPLE = [
    {"name": "Бородинский", "price": 150},
    {"name": "Ржаной", "price": 120},
]


@pytest.fixture(autouse=True)
def tmp_bread_file(tmp_path, monkeypatch):
    bread_file = tmp_path / "bread.csv"
    monkeypatch.setattr(bs, "BREAD_FILE", bread_file)
    # Записываем начальные данные
    with open(bread_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for item in SAMPLE:
            writer.writerow([item["name"], item["price"]])
    return bread_file


def test_load_bread_returns_list():
    items = bs.load_bread()
    assert len(items) == 2
    assert items[0]["name"] == "Бородинский"
    assert items[0]["price"] == 150


def test_load_bread_missing_file(monkeypatch, tmp_path):
    monkeypatch.setattr(bs, "BREAD_FILE", tmp_path / "missing.csv")
    assert bs.load_bread() == []


def test_save_and_load_roundtrip():
    new_items = [{"name": "Багет", "price": 90}]
    bs.save_bread(new_items)
    assert bs.load_bread() == new_items


def test_add_bread_new():
    bs.add_bread("Пшеничный", 100)
    items = bs.load_bread()
    names = [i["name"] for i in items]
    assert "Пшеничный" in names


def test_add_bread_duplicate_raises():
    with pytest.raises(ValueError, match="уже есть"):
        bs.add_bread("Бородинский", 200)


def test_add_bread_case_insensitive_duplicate():
    with pytest.raises(ValueError):
        bs.add_bread("бородинский", 200)


def test_remove_bread_existing():
    bs.remove_bread("Ржаной")
    items = bs.load_bread()
    assert all(i["name"] != "Ржаной" for i in items)


def test_remove_bread_not_found_raises():
    with pytest.raises(ValueError, match="не найден"):
        bs.remove_bread("Несуществующий")


def test_list_bread_format():
    text = bs.list_bread()
    assert "Бородинский" in text
    assert "150" in text
    assert "Ржаной" in text


def test_list_bread_empty(monkeypatch, tmp_path):
    empty_file = tmp_path / "empty.csv"
    empty_file.write_text("")
    monkeypatch.setattr(bs, "BREAD_FILE", empty_file)
    assert bs.list_bread() == "Ассортимент пуст"

"""Простое файловое FSM-хранилище на основе pickle для aiogram 3."""
import pickle
from pathlib import Path
from typing import Any, Dict, Optional

from aiogram.fsm.storage.base import BaseStorage, StorageKey, StateType

STORAGE_FILE = Path(__file__).parent.parent / "data" / "fsm_storage.pkl"


class PickleStorage(BaseStorage):
    def __init__(self, path: Path = STORAGE_FILE):
        self._path = path
        self._data: Dict[str, Dict] = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            try:
                with open(self._path, "rb") as f:
                    return pickle.load(f)
            except Exception:
                return {}
        return {}

    def _dump(self):
        with open(self._path, "wb") as f:
            pickle.dump(self._data, f)

    def _k(self, key: StorageKey) -> str:
        return f"{key.bot_id}:{key.chat_id}:{key.user_id}"

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        k = self._k(key)
        self._data.setdefault(k, {})
        self._data[k]["state"] = state.state if hasattr(state, "state") else state
        self._dump()

    async def get_state(self, key: StorageKey) -> Optional[str]:
        return self._data.get(self._k(key), {}).get("state")

    async def set_data(self, key: StorageKey, data: Dict[str, Any]) -> None:
        k = self._k(key)
        self._data.setdefault(k, {})
        self._data[k]["data"] = data
        self._dump()

    async def get_data(self, key: StorageKey) -> Dict[str, Any]:
        return self._data.get(self._k(key), {}).get("data", {})

    async def close(self) -> None:
        self._dump()

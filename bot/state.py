"""Хранение шага диалога по каждому чату (JSON-файл на диске)."""
from __future__ import annotations

import json
import os
import threading

MAX_SEEN = 100


class ChatState:
    """Мини-хранилище: шаг диалога + последние id сообщений от дублей."""

    def __init__(self, path: str) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._steps: dict[str, int] = {}
        self._seen: dict[str, list[str]] = {}
        self._load()

    def _load(self) -> None:
        try:
            with open(self._path, "r", encoding="utf-8-sig") as fh:
                raw = json.load(fh)
        except (OSError, ValueError):
            return
        if not isinstance(raw, dict):
            return
        chats = raw.get("chats") or {}
        if isinstance(chats, dict):
            for key, value in chats.items():
                try:
                    self._steps[str(key)] = int(value)
                except (TypeError, ValueError):
                    continue
        seen = raw.get("seen") or {}
        if isinstance(seen, dict):
            for key, value in seen.items():
                if isinstance(value, list):
                    self._seen[str(key)] = [str(v) for v in value][-MAX_SEEN:]

    def _save(self) -> None:
        folder = os.path.dirname(self._path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        tmp = self._path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"chats": self._steps, "seen": self._seen}, fh, ensure_ascii=False)
        os.replace(tmp, self._path)

    def step(self, chat_id) -> int:
        with self._lock:
            return int(self._steps.get(str(chat_id), 0))

    def set_step(self, chat_id, step: int) -> None:
        with self._lock:
            if self._steps.get(str(chat_id)) == step:
                return
            self._steps[str(chat_id)] = int(step)
            self._save()

    def is_duplicate(self, chat_id, message_id) -> bool:
        """True, если такое id сообщения в этом чате уже обрабатывали."""
        if message_id is None:
            return False
        key = str(chat_id)
        marker = str(message_id)
        with self._lock:
            ids = self._seen.setdefault(key, [])
            if marker in ids:
                return True
            ids.append(marker)
            if len(ids) > MAX_SEEN:
                del ids[: len(ids) - MAX_SEEN]
            self._save()
            return False

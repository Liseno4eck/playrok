"""Клиент Playerok: слушает чаты и отвечает покупателям.

Работает через неофициальную библиотеку PlayerokAPI (авторизация cookie).
Весь ввод-вывод с площадкой изолирован здесь, чтобы легко заменить способ
подключения, если Playerok что-то поменяет.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Iterator

from .config import Config

log = logging.getLogger("bot.playerok")

RECONNECT_DELAY = 15


@dataclass
class BuyerMessage:
    """Одно сообщение покупателя в чате."""

    chat_id: object
    user_id: object
    username: object
    text: str
    message_id: object


class PlayerokClient:
    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg
        self._acc = None
        self.my_id = None

    def connect(self) -> None:
        from playerokapi.account import Account

        log.info("Вход в Playerok...")
        self._acc = Account(
            cookies=self._cfg.playerok_cookies,
            user_agent=self._cfg.playerok_user_agent,
        ).get()
        self.my_id = getattr(self._acc, "id", None)
        log.info("Playerok: вошли, id аккаунта = %s", self.my_id)

    def send(self, chat_id, text: str) -> bool:
        try:
            self._acc.send_message(chat_id=chat_id, text=text)
            return True
        except Exception as exc:
            log.error("Playerok: не отправлено в чат %s: %s", chat_id, exc)
            return False

    def events(self) -> Iterator[BuyerMessage]:
        """Бесконечный поток сообщений покупателя с переподключением."""
        from playerokapi.enums import EventTypes
        from playerokapi.listener.listener import EventListener

        while True:
            try:
                if self._acc is None:
                    self.connect()
                listener = EventListener(self._acc)
                log.info("Слушаю чаты Playerok...")
                for event in listener.listen():
                    message = self._normalize(event, EventTypes)
                    if message is not None:
                        yield message
            except GeneratorExit:
                raise
            except Exception as exc:
                log.warning(
                    "Playerok: поток событий оборвался (%s), переподключение через %s с",
                    exc,
                    RECONNECT_DELAY,
                )
                self._acc = None
                time.sleep(RECONNECT_DELAY)

    def _normalize(self, event, event_types) -> BuyerMessage | None:
        if getattr(event, "type", None) is not event_types.NEW_MESSAGE:
            return None

        message = getattr(event, "message", None) or event
        user = getattr(message, "user", None)
        user_id = getattr(user, "id", None)
        if self.my_id is not None and user_id == self.my_id:
            return None  # наше же сообщение

        text = getattr(message, "text", None)
        if not text or not str(text).strip():
            return None  # пустые сообщения и вложения игнорируем

        chat = getattr(event, "chat", None)
        chat_id = getattr(chat, "id", None) or user_id
        return BuyerMessage(
            chat_id=chat_id,
            user_id=user_id,
            username=getattr(user, "username", None),
            text=str(text),
            message_id=getattr(message, "id", None),
        )

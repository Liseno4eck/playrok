"""Клиент Playerok: REST-polling чатов вместо WebSocket.

Поскольку в playerokapi нет встроенного EventListener,
реализуем polling через get_chats() + get_chat_messages().
"""
from __future__ import annotations

import logging
import os
import shutil
import time
from dataclasses import dataclass
from typing import Iterator

from .config import Config

log = logging.getLogger("bot.playerok")

POLL_INTERVAL = 10
RECONNECT_DELAY = 15


def ensure_cacert() -> None:
    """playerokapi ищет cacert.pem внутри своей папки, но не кладёт его туда.

    Копируем системный набор корневым сертификатов (certifi) под нужным именем.
    """
    try:
        import playerokapi

        target = os.path.join(os.path.dirname(playerokapi.__file__), "cacert.pem")
        if os.path.exists(target):
            return
        import certifi

        shutil.copyfile(certifi.where(), target)
        log.info("Создан файл сертификатов: %s", target)
    except Exception as exc:
        log.warning("Не удалось подготовить cacert.pem: %s", exc)


@dataclass
class BuyerMessage:
    """Одно сообщение покупателя в чате."""

    chat_id: str
    user_id: str
    username: str | None
    text: str
    message_id: str | None


class PlayerokClient:
    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg
        self._acc = None
        self.my_id = None

    def connect(self) -> None:
        ensure_cacert()
        from playerokapi.account import Account

        log.info("Вход в Playerok...")
        self._acc = Account(
            cookies=self._cfg.playerok_cookies,
            user_agent=self._cfg.playerok_user_agent,
        ).get()
        self.my_id = str(self._acc.id)
        log.info("Playerok: вошли, id аккаунта = %s", self.my_id)

    def send(self, chat_id: str, text: str) -> bool:
        try:
            self._acc.send_message(chat_id=chat_id, text=text)
            return True
        except Exception as exc:
            log.error("Playerok: не отправлено в чат %s: %s", chat_id, exc)
            return False

    def events(self) -> Iterator[BuyerMessage]:
        """Бесконечный поллинг: get_chats -> get_chat_messages."""
        last_seen: dict[str, str] = {}  # chat_id -> last_message_id

        while True:
            try:
                if self._acc is None:
                    self.connect()

                chats = self._acc.get_chats(count=24)
                if chats and hasattr(chats, "chats"):
                    for chat in chats.chats:
                        chat_id = getattr(chat, "id", None)
                        if not chat_id:
                            continue
                        chat_id = str(chat_id)

                        # Пропускаем чат с моим id (собственные сообщения)
                        if getattr(chat, "user", None):
                            try:
                                uid = str(getattr(chat.user, "id", ""))
                                if uid == self.my_id:
                                    continue
                            except Exception:
                                pass

                        # Получаем новые сообщения
                        try:
                            msgs = self._acc.get_chat_messages(
                                chat_id=chat_id, count=24
                            )
                        except Exception as exc:
                            log.warning("get_chat_messages %s: %s", chat_id, exc)
                            continue

                        if not msgs or not hasattr(msgs, "messages"):
                            continue

                        for msg in msgs.messages:
                            msg_id = str(getattr(msg, "id", ""))
                            if not msg_id:
                                continue

                            # Пропускаем уже обработанные
                            if msg_id == last_seen.get(chat_id):
                                continue

                            # Пропускаем наши сообщения
                            try:
                                sender = getattr(msg, "sender", None) or getattr(msg, "user", None)
                                if sender:
                                    sid = str(getattr(sender, "id", ""))
                                    if sid == self.my_id:
                                        continue
                            except Exception:
                                pass

                            text = getattr(msg, "text", None)
                            if not text or not str(text).strip():
                                continue  # пустые / вложения

                            username = None
                            try:
                                sender = getattr(msg, "sender", None) or getattr(msg, "user", None)
                                if sender:
                                    username = getattr(sender, "username", None)
                            except Exception:
                                pass

                            last_seen[chat_id] = msg_id
                            yield BuyerMessage(
                                chat_id=chat_id,
                                user_id=str(getattr(msg, "sender_id", chat_id)),
                                username=username,
                                text=str(text),
                                message_id=msg_id,
                            )
            except GeneratorExit:
                raise
            except Exception as exc:
                log.warning(
                    "Playerok: поллинг упал (%s), переподключение через %s с",
                    exc,
                    RECONNECT_DELAY,
                )
                self._acc = None
                time.sleep(RECONNECT_DELAY)

            time.sleep(POLL_INTERVAL)

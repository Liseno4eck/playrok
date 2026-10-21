"""Связка: чаты Playerok -> диалог -> уведомления продавцу в VK."""
from __future__ import annotations

import logging
import time

from . import flow
from .config import Config
from .playerok import BuyerMessage, PlayerokClient
from .state import ChatState
from .vk import VkNotifier

log = logging.getLogger("bot.app")

RESTART_DELAY = 15


class Bot:
    def __init__(
        self,
        cfg: Config,
        client: PlayerokClient,
        vk: VkNotifier,
        state: ChatState,
    ) -> None:
        self._cfg = cfg
        self._client = client
        self._vk = vk
        self._state = state

    def handle(self, msg: BuyerMessage) -> None:
        """Обработать одно сообщение покупателя."""
        if self._state.is_duplicate(msg.chat_id, msg.message_id):
            return

        step = self._state.step(msg.chat_id)
        buyer_link = self._cfg.profile_link(msg.username, msg.user_id)
        chat_link = self._cfg.chat_link(msg.chat_id)
        decision = flow.decide(step, msg.text, buyer_link, chat_link)

        for note in decision.vk_notifications:
            if not self._vk.send(note):
                log.error("VK: уведомление не дошло: %s", note[:80])

        for reply in decision.playerok_replies:
            self._client.send(msg.chat_id, reply)

        if decision.next_step != step:
            self._state.set_step(msg.chat_id, decision.next_step)
            log.info(
                "Чат %s: шаг %s -> %s", msg.chat_id, step, decision.next_step
            )

    def run_forever(self) -> None:
        while True:
            try:
                for msg in self._client.events():
                    try:
                        self.handle(msg)
                    except Exception:
                        log.exception("Ошибка на сообщении из чата %s", msg.chat_id)
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                log.error("Цикл бота упал: %s. Рестарт через %s с", exc, RESTART_DELAY)
                time.sleep(RESTART_DELAY)


def build(cfg: Config) -> Bot:
    return Bot(
        cfg,
        PlayerokClient(cfg),
        VkNotifier(cfg),
        ChatState(cfg.state_file),
    )

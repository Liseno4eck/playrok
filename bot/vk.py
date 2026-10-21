"""Уведомления продавцу в VK через токен сообщества."""
from __future__ import annotations

import logging
import secrets
import time

from .config import Config

log = logging.getLogger("bot.vk")


class VkNotifier:
    """Шлёт сообщения продавцу (можно несколько id через запятую)."""

    def __init__(self, cfg: Config) -> None:
        import vk_api  # импорт здесь, чтобы логика тестилась без библиотеки

        self._cfg = cfg
        self._api = vk_api.VkApi(token=cfg.vk_group_token).get_api()

    def send(self, text: str) -> bool:
        """True, если текст ушёл хотя бы одному продавцу."""
        ok = False
        for user_id in self._cfg.vk_seller_ids:
            for attempt in (1, 2):
                try:
                    self._api.messages.send(
                        user_id=user_id,
                        message=text,
                        random_id=secrets.randbelow(2_000_000_000),
                        disable_mentions=1,
                    )
                    ok = True
                    break
                except Exception as exc:  # сеть, лимиты, доступность диалогов
                    log.warning(
                        "VK: не отправлено (попытка %s, user %s): %s",
                        attempt,
                        user_id,
                        exc,
                    )
                    if attempt == 1:
                        time.sleep(2)
        return ok

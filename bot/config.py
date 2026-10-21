"""Загрузка настроек из переменных окружения (и .env)."""
from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigError(RuntimeError):
    """Не хватает или неверно заданы переменные окружения."""


def load_dotenv(path: str = ".env") -> None:
    """Простой читатель .env (не перекрывает уже заданные переменные)."""
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


@dataclass(frozen=True)
class Config:
    playerok_cookies: str
    playerok_user_agent: str
    vk_group_token: str
    vk_seller_ids: tuple[int, ...]
    playerok_base_url: str = "https://playerok.com"
    profile_url_template: str = "{base}/u/{username}"
    chat_url_template: str = "{base}/chats/{chat_id}"
    state_file: str = "data/state.json"
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Config":
        load_dotenv()
        missing = []

        def req(name):
            val = os.getenv(name, "").strip()
            if not val:
                missing.append(name)
            return val

        cookies = req("PLAYEROK_COOKIES")
        ua = req("PLAYEROK_USER_AGENT")
        token = req("VK_GROUP_TOKEN")
        sellers_raw = req("VK_SELLER_USER_IDS")

        if missing:
            raise ConfigError("Не заданы переменные: " + ", ".join(missing))

        ids = []
        for part in sellers_raw.replace(";", ",").split(","):
            part = part.strip()
            if not part:
                continue
            try:
                ids.append(int(part))
            except ValueError:
                raise ConfigError(
                    f"VK_SELLER_USER_IDS содержит не число: {part}"
                )

        if not ids:
            raise ConfigError(
                "VK_SELLER_USER_IDS должен содержать хотя бы один числовой id"
            )

        return cls(
            playerok_cookies=cookies,
            playerok_user_agent=ua,
            vk_group_token=token,
            vk_seller_ids=tuple(ids),
            playerok_base_url=os.getenv(
                "PLAYEROK_BASE_URL", "https://playerok.com"
            ).strip().rstrip("/"),
            profile_url_template=os.getenv(
                "PLAYEROK_PROFILE_URL", "{base}/u/{username}"
            ).strip(),
            chat_url_template=os.getenv(
                "PLAYEROK_CHAT_URL", "{base}/chats/{chat_id}"
            ).strip(),
            state_file=os.getenv("STATE_FILE", "data/state.json").strip(),
            log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
        )

    def profile_link(self, username: str | None, user_id) -> str:
        if username:
            return self.profile_url_template.format(
                base=self.playerok_base_url, username=username, user_id=user_id
            )
        return self.chat_url_template.format(
            base=self.playerok_base_url, chat_id=user_id
        )

    def chat_link(self, chat_id) -> str:
        return self.chat_url_template.format(
            base=self.playerok_base_url, chat_id=chat_id
        )

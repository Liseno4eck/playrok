"""Точка входа: python main.py"""
from __future__ import annotations

import argparse
import logging
import sys

from bot.app import build
from bot.config import Config, ConfigError


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        stream=sys.stdout,
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Playerok-бот с уведомлениями в VK",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="проверить настройки и выйти без запуска",
    )
    args = parser.parse_args(argv)

    try:
        cfg = Config.from_env()
    except ConfigError as exc:
        print(f"Ошибка конфигурации: {exc}", file=sys.stderr)
        return 2

    setup_logging(cfg.log_level)
    log = logging.getLogger("main")

    if args.check:
        log.info(
            "Конфигурация OK. Продавцы: %s",
            ", ".join(map(str, cfg.vk_seller_ids)),
        )
        log.info(
            "Шаблоны ссылок: %s  |  %s",
            cfg.profile_url_template,
            cfg.chat_url_template,
        )
        return 0

    bot = build(cfg)
    log.info("Бот запущен")
    try:
        bot.run_forever()
    except KeyboardInterrupt:
        log.info("Остановлен по Ctrl+C")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

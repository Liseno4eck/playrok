"""Чистая логика диалога: без сети и диска - только шаги и тексты.

Шаги диалога:
    0 NEW          - покупателю ещё ничего не отправляли
    1 ASK_TYPE     - задан вопрос "какой бот нужен", ждём +от
    2 ASK_DELIVERY - задан вопрос "готовый бот или код", ждём +от
    3 ASK_ACCOUNT  - задан вопрос "ссылка на аккаунт / username", ждём +от
    4 DONE         - ответы собраны, продавец уведомлён
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import texts

NEW = 0
ASK_TYPE = 1
ASK_DELIVERY = 2
ASK_ACCOUNT = 3
DONE = 4

EXTRA_LABEL = "дополнение"


@dataclass
class Decision:
    """Что нужно сделать по итогам одного сообщения покупателя."""

    next_step: int
    playerok_replies: list[str] = field(default_factory=list)
    vk_notifications: list[str] = field(default_factory=list)


def _unwrap(payload: str) -> str:
    """Снять скобки, если покупатель написал "+от (мой текст)"."""
    payload = payload.strip()
    if len(payload) > 1 and payload.startswith("(") and payload.endswith(")"):
        return payload[1:-1].strip()
    return payload


def parse_command(text: str) -> tuple[str | None, str]:
    """Вернуть (команда, полезная нагрузка) либо (None, исходный текст)."""
    raw = (text or "").strip().strip("\u200b\u2005\ufeff").strip()
    if not raw:
        return None, ""
    lowered = raw.lower().replace("\u200b", "").replace("\u2005", " ")
    for cmd in (texts.CMD_ANSWER, texts.CMD_CALL):
        prefix = "+" + cmd
        if lowered == prefix:
            return cmd, ""
        if lowered.startswith(prefix):
            tail = lowered[len(prefix):]
            if tail[:1] in (" ", ":", ";", "-", "\u2014", "\u2013", ","):
                return cmd, _unwrap(raw[len(prefix):].strip(" :;,-\u2014\u2013"))
    return None, raw


def _label(step: int) -> str | int:
    return EXTRA_LABEL if step == DONE else step


def decide(step: int, text: str, buyer_link: str, chat_link: str) -> Decision:
    """Главная функция диалога: шаг + текст сообщения -> действия."""
    cmd, payload = parse_command(text)
    out = Decision(next_step=step)

    # Сообщение без команды.
    if cmd is None:
        if step == NEW:
            out.playerok_replies.append(texts.QUESTION_1)
            out.next_step = ASK_TYPE
        elif step == DONE:
            out.vk_notifications.append(
                texts.vk_message(buyer_link, raw_text(text), _label(step))
            )
            out.playerok_replies.append(texts.RECEIVED_OK)
        else:
            out.playerok_replies.append(texts.HOW_TO_ANSWER)
        return out

    # Команда пришла самым первым сообщением - сначала приветствие.
    if step == NEW:
        out.playerok_replies.append(texts.QUESTION_1)
        step = ASK_TYPE
        out.next_step = step

    # +позвать: уведомляем продавца в VK, шаг диалога не меняем.
    if cmd == texts.CMD_CALL:
        out.vk_notifications.append(texts.vk_call(chat_link))
        out.playerok_replies.append(texts.CALLED_OK)
        return out

    # +от без текста.
    if not payload:
        out.playerok_replies.append(texts.NEED_TEXT)
        return out

    # +от <текст>: пересылаем продавцу и идём по диалогу дальше.
    out.vk_notifications.append(texts.vk_message(buyer_link, payload, _label(step)))

    if step == ASK_TYPE:
        out.playerok_replies.append(texts.QUESTION_2)
        out.next_step = ASK_DELIVERY
    elif step == ASK_DELIVERY:
        out.playerok_replies.append(texts.QUESTION_3)
        out.next_step = ASK_ACCOUNT
    elif step == ASK_ACCOUNT:
        out.playerok_replies.append(texts.FINISHED)
        out.next_step = DONE
    else:
        out.playerok_replies.append(texts.RECEIVED_OK)
    return out


def raw_text(text: str) -> str:
    return (text or "").strip()

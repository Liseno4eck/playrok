"""Тесты чистой логики диалога (без сети и зависимостей)."""
from __future__ import annotations

import sys
import os

# Добавляем корень репозитория в sys.path, чтобы тесты работали из любой папки.
repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, repo)

from bot import flow, texts


def _assert_replies(decision, *expected_playerok):
    """Проверка: что бот отправил покупателю."""
    assert decision.playerok_replies == list(expected_playerok), (
        f"playerok_replies:\n"
        f"  получено: {decision.playerok_replies}\n"
        f"  ожидалось: {expected_playerok}"
    )


def _assert_vk(decision, *expected_vk):
    """Проверка: что бот отправил продавцу в VK."""
    assert decision.vk_notifications == list(expected_vk), (
        f"vk_notifications:\n"
        f"  получено: {decision.vk_notifications}\n"
        f"  ожидалось: {expected_vk}"
    )


def _assert_step(decision, expected_step):
    assert decision.next_step == expected_step, (
        f"next_step: {decision.next_step} != {expected_step}"
    )


def test_new_message_plain_text():
    """Новый покупатель, первое сообщение — приветствие."""
    d = flow.decide(flow.NEW, "Привет, есть бот?", "link", "chat")
    _assert_step(d, flow.ASK_TYPE)
    _assert_replies(d, texts.QUESTION_1)


def test_new_plus_call():
    """Первое сообщение — позвать продавца."""
    d = flow.decide(flow.NEW, "+позвать", "link", "chat")
    _assert_step(d, flow.ASK_TYPE)
    _assert_replies(d, texts.QUESTION_1, texts.CALLED_OK)
    assert len(d.vk_notifications) == 1 and texts.vk_call("chat") in d.vk_notifications[0]


def test_answer_1():
    """Ответ на первый вопрос: +от <текст> -> вопрос 2."""
    d = flow.decide(flow.ASK_TYPE, "+от мне нужен бот для выдачи товаров", "link", "chat")
    _assert_step(d, flow.ASK_DELIVERY)
    _assert_replies(d, texts.QUESTION_2)
    assert len(d.vk_notifications) == 1


def test_answer_2():
    """Ответ на второй вопрос: +от <текст> -> вопрос 3."""
    d = flow.decide(flow.ASK_DELIVERY, "+от готовый", "link", "chat")
    _assert_step(d, flow.ASK_ACCOUNT)
    _assert_replies(d, texts.QUESTION_3)


def test_answer_3():
    """Ответ на третий вопрос: +от <текст> -> финал."""
    d = flow.decide(flow.ASK_ACCOUNT, "+от link_to_account", "link", "chat")
    _assert_step(d, flow.DONE)
    _assert_replies(d, texts.FINISHED)


def test_call_any_step():
    """+позвать в любом шаге -> уведомление продавцу."""
    for step in (flow.ASK_TYPE, flow.ASK_DELIVERY, flow.ASK_ACCOUNT, flow.DONE):
        d = flow.decide(step, "+позвать", "link", "chat")
        assert len(d.vk_notifications) == 1


def test_plus_ot_without_text():
    """+от без текста -> бот просит написать."""
    d = flow.decide(flow.ASK_TYPE, "+от", "link", "chat")
    _assert_step(d, flow.ASK_TYPE)
    _assert_replies(d, texts.NEED_TEXT)


def test_no_command():
    """Сообщение без команды -> напоминание."""
    d = flow.decide(flow.ASK_TYPE, "хочу бота", "link", "chat")
    _assert_step(d, flow.ASK_TYPE)
    _assert_replies(d, texts.HOW_TO_ANSWER)


def test_done_extra_message():
    """После завершения: любое сообщение пересылается продавцу."""
    d = flow.decide(flow.DONE, "ещё нужно добавить поддержку тг", "link", "chat")
    _assert_step(d, flow.DONE)
    _assert_replies(d, texts.RECEIVED_OK)


def test_parse_command():
    d1, p1 = flow.parse_command("+от текст")
    assert d1 == "от" and p1 == "текст"
    d2, p2 = flow.parse_command("+позвать")
    assert d2 == "позвать" and p2 == ""
    d3, p3 = flow.parse_command("обычное сообщение")
    assert d3 is None and p3 == "обычное сообщение"
    d4, p4 = flow.parse_command("+от (текст в скобках)")
    assert d4 == "от" and p4 == "текст в скобках"


def run_all():
    """Запуск всех тестов без pytest."""
    funcs = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in funcs:
        try:
            fn()
            print(f"  OK  {fn.__name__}")
        except Exception as exc:
            print(f"FAIL {fn.__name__}: {exc}")
            failed += 1
    total = len(funcs)
    print(f"\nРезультат: {total - failed}/{total} пройдено")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(run_all())

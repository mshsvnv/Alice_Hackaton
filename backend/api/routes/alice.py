"""
Маршрут вебхука для интеграции с навыком Алисы.

Обрабатывает входящие запросы от Яндекс.Диалогов,
определяет намерение пользователя и формирует ответ.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

from backend.models.schemas import (
    AliceRequest,
    AliceResponse,
    DisabilityType,
    KnowledgeHintRequest,
)
from backend.services.adaptation_service import AdaptationService
from backend.services.document_service import DocumentService
from backend.services.knowledge_base_service import KnowledgeBaseService
from backend.services.profile_service import ProfileService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Алиса"])


# ──────────────────────────── Обработчик диалога ──────────────────────


async def _handle_alice_request(request: AliceRequest) -> AliceResponse:
    """Основной обработчик запросов от Алисы.

    Определяет намерение пользователя и вызывает соответствующий сервис.

    Args:
        request: Входящий запрос от Алисы.

    Returns:
        Ответ для Алисы.
    """
    # Извлекаем данные из запроса
    req = request.request
    command = req.get("command", "").strip().lower()
    original_utterance = req.get("original_utterance", "").strip()
    session = request.session
    user_id = session.get("user", {}).get("user_id", "anonymous")

    # Получаем состояние сессии
    state = request.state or {}
    session_state = request.session.get("state", {}) if "state" in request.session else {}

    # Определяем текущий шаг сценария
    current_step = session_state.get("step", "start")

    logger.info(f"Алиса: command='{command}', user_id='{user_id}', step='{current_step}'")

    # ─── Начало диалога ───
    if current_step == "start" and not command:
        return _make_response(
            text=(
                "Здравствуйте! Я — Алиса, ваш помощник в обучении. "
                "Я могу помочь вам пройти тест, найти подсказку или адаптировать задание. "
                "Скажите «тест», «подсказка» или «адаптировать»."
            ),
            tts=(
                "Здравствуйте! Я — Алиса, ваш помощник в обучении. "
                "Я могу помочь вам пройти тест, найти подсказку или адаптировать задание. "
                "Скажите «тест», «подсказка» или «адаптировать»."
            ),
            session_state={"step": "menu"},
        )

    # ─── Меню: выбор действия ───
    if current_step == "menu" or (current_step == "start" and command):
        # Запрос подсказки
        if any(word in command for word in ("подсказк", "помог", "объясни", "что такое", "не понимаю")):
            return await _handle_hint_request(command, original_utterance, user_id, session_state)

        # Запрос на адаптацию теста
        if any(word in command for word in ("адаптир", "упрости", "переделай")):
            return _make_response(
                text="Для какого типа ОВЗ адаптировать тест? Скажите: «слабовидение», «когнитивные» или «ОДА».",
                tts="Для какого типа ОВЗ адаптировать тест? Скажите: «слабовидение», «когнитивные» или «ОДА».",
                session_state={"step": "adapt_select_type"},
            )

        # Запрос на прохождение теста
        if "тест" in command:
            return _make_response(
                text="Хотите пройти тест? Скажите «да» для начала.",
                tts="Хотите пройти тест? Скажите «да» для начала.",
                session_state={"step": "test_confirm"},
            )

        # Приветствие
        if any(word in command for word in ("привет", "здравствуй", "добрый")):
            return _make_response(
                text="Здравствуйте! Чем могу помочь? Скажите «тест», «подсказка» или «адаптировать».",
                tts="Здравствуйте! Чем могу помочь? Скажите «тест», «подсказка» или «адаптировать».",
                session_state={"step": "menu"},
            )

        # Помощь
        if any(word in command for word in ("помощь", "помоги", "что ты умеешь", "что можешь")):
            return _make_response(
                text=(
                    "Я умею: 1) Помогать с подсказками во время теста — скажите «подсказка». "
                    "2) Адаптировать тест под ваши потребности — скажите «адаптировать». "
                    "3) Проводить тестирование — скажите «тест»."
                ),
                tts=(
                    "Я умею: во-первых, помогать с подсказками во время теста — скажите «подсказка». "
                    "Во-вторых, адаптировать тест под ваши потребности — скажите «адаптировать». "
                    "В-третьих, проводить тестирование — скажите «тест»."
                ),
                session_state={"step": "menu"},
            )

        # Неизвестная команда
        return _make_response(
            text="Я не совсем поняла. Скажите «тест», «подсказка» или «адаптировать».",
            tts="Я не совсем поняла. Скажите «тест», «подсказка» или «адаптировать».",
            session_state={"step": "menu"},
        )

    # ─── Выбор типа ОВЗ для адаптации ───
    if current_step == "adapt_select_type":
        disability_type = _parse_disability_type(command)
        if disability_type is None:
            return _make_response(
                text="Пожалуйста, выберите тип: «слабовидение», «когнитивные» или «ОДА».",
                tts="Пожалуйста, выберите тип: «слабовидение», «когнитивные» или «ОДА».",
                session_state={"step": "adapt_select_type"},
            )

        # Демонстрационная адаптация с примером теста
        sample_test = {
            "id": "demo_test",
            "title": "Демонстрационный тест по биологии",
            "questions": [
                {
                    "id": "q1",
                    "text": "Что такое фотосинтез?",
                    "options": [
                        "Процесс, при котором растения поглощают воду из почвы.",
                        "Процесс, при котором растения производят свою пищу с помощью солнечного света.",
                        "Процесс, при котором растения выделяют кислород в почву.",
                        "Процесс, при котором растения растут в высоту.",
                    ],
                    "correct_option_index": 1,
                }
            ],
        }

        adapted = await AdaptationService.create_adapted_test(
            sample_test, disability_type, use_gpt=False
        )

        first_question = adapted["questions"][0] if adapted["questions"] else None
        if first_question:
            options_text = ". ".join(
                f"{chr(1040 + i)}) {opt}" for i, opt in enumerate(first_question["options"])
            )
            response_text = (
                f"Тест адаптирован для типа «{disability_type.value}». "
                f"Первый вопрос: {first_question['text']} "
                f"Варианты: {options_text}. "
                "Скажите «подсказка», если нужна помощь."
            )
        else:
            response_text = "Тест адаптирован, но вопросы не найдены."

        return _make_response(
            text=response_text,
            tts=response_text,
            session_state={"step": "menu", "adapted_test_id": adapted["id"]},
        )

    # ─── Подтверждение теста ───
    if current_step == "test_confirm":
        if any(word in command for word in ("да", "начать", "давай", "хочу")):
            return _make_response(
                text="Тест начат! Я буду зачитывать вопросы. Скажите номер ответа (1, 2, 3 или 4) или букву (А, Б, В, Г). Для подсказки скажите «подсказка».",
                tts="Тест начат! Я буду зачитывать вопросы. Скажите номер ответа: 1, 2, 3 или 4, или букву: А, Б, В, Г. Для подсказки скажите подсказка.",
                session_state={"step": "test_in_progress", "current_question": 0},
            )
        else:
            return _make_response(
                text="Хорошо, тест отменён. Чем ещё могу помочь?",
                tts="Хорошо, тест отменён. Чем ещё могу помочь?",
                session_state={"step": "menu"},
            )

    # ─── Тест в процессе ───
    if current_step == "test_in_progress":
        if any(word in command for word in ("подсказк", "помог", "объясни", "не понимаю")):
            return await _handle_hint_request(command, original_utterance, user_id, session_state)

        if any(word in command for word in ("повтори", "ещё раз")):
            return _make_response(
                text="Повторяю вопрос. (В прототипе вопрос повторяется.)",
                tts="Повторяю вопрос. (В прототипе вопрос повторяется.)",
                session_state=session_state,
            )

        if any(word in command for word in ("перерыв", "пауз", "стоп")):
            return _make_response(
                text="Тест приостановлен. Скажите «продолжить», когда будете готовы.",
                tts="Тест приостановлен. Скажите «продолжить», когда будете готовы.",
                session_state={**session_state, "step": "test_paused"},
            )

        # Обработка ответа (буква А, Б, В, Г или цифра 1, 2, 3, 4)
        answer_map = {"а": 0, "б": 1, "в": 2, "г": 3}
        digit_map = {"1": 0, "2": 1, "3": 2, "4": 3}
        word_map = {
            "первый": 0, "второй": 1, "третий": 2, "четвёртый": 3, "четвертый": 3,
            "один": 0, "два": 1, "три": 2, "четыре": 3,
        }

        answer_index = None
        answer_label = ""

        if command in answer_map:
            answer_index = answer_map[command]
            answer_label = command.upper()
        elif command in digit_map:
            answer_index = digit_map[command]
            answer_label = command
        else:
            for word, idx in word_map.items():
                if word in command:
                    answer_index = idx
                    answer_label = str(idx + 1)
                    break

        if answer_index is not None:
            return _make_response(
                text=f"Вы выбрали вариант {answer_label}. Записываю ответ. Переходим к следующему вопросу.",
                tts=f"Вы выбрали вариант {answer_label}. Записываю ответ. Переходим к следующему вопросу.",
                session_state=session_state,
            )

        return _make_response(
            text="Скажите номер ответа: 1, 2, 3 или 4. Или букву: А, Б, В или Г. Или попросите подсказку.",
            tts="Скажите номер ответа: 1, 2, 3 или 4. Или букву: А, Б, В или Г. Или попросите подсказку.",
            session_state=session_state,
        )

    # ─── Тест на паузе ───
    if current_step == "test_paused":
        if any(word in command for word in ("продолж", "дальше", "возобнов")):
            return _make_response(
                text="Продолжаем тест. (В прототипе — возврат к вопросу.)",
                tts="Продолжаем тест. (В прототипе — возврат к вопросу.)",
                session_state={**session_state, "step": "test_in_progress"},
            )
        return _make_response(
            text="Тест на паузе. Скажите «продолжить», когда будете готовы.",
            tts="Тест на паузе. Скажите «продолжить», когда будете готовы.",
            session_state=session_state,
        )

    # ─── Fallback ───
    return _make_response(
        text="Я не поняла. Скажите «тест», «подсказка» или «адаптировать».",
        tts="Я не поняла. Скажите «тест», «подсказка» или «адаптировать».",
        session_state={"step": "menu"},
    )


# ──────────────────────────── Обработчик подсказок ────────────────────


async def _handle_hint_request(
    command: str,
    original_utterance: str,
    user_id: str,
    session_state: dict[str, Any],
) -> AliceResponse:
    """Обрабатывает запрос подсказки через RAG.

    Args:
        command: Нормализованная команда пользователя.
        original_utterance: Оригинальная фраза пользователя.
        user_id: Идентификатор пользователя.
        session_state: Текущее состояние сессии.

    Returns:
        Ответ Алисы с подсказкой.
    """
    # Извлекаем суть запроса (убираем служебные слова)
    query = original_utterance
    for prefix in ("алиса", "подскажи", "помоги", "объясни"):
        query = query.lower().replace(prefix, "").strip()

    if not query:
        query = command

    # Ищем подсказку в базе знаний
    hint_request = KnowledgeHintRequest(
        user_query=query,
        user_profile_id=user_id,
        current_question_text=session_state.get("current_question_text"),
    )
    hint = await KnowledgeBaseService.get_hint(hint_request)

    response_text = f"Вот что я нашла: {hint.hint_text}"
    if hint.confidence < 0.3:
        response_text = f"Попробую объяснить: {hint.hint_text}"

    return _make_response(
        text=response_text,
        tts=response_text,
        session_state=session_state,
    )


# ──────────────────────────── Вспомогательные функции ────────────────


def _parse_disability_type(command: str) -> DisabilityType | None:
    """Определяет тип ОВЗ из команды пользователя."""
    if any(word in command for word in ("слабовид", "зрен", "слеп", "визуал")):
        return DisabilityType.VISION
    if any(word in command for word in ("когнитив", "памят", "вниман", "поним")):
        return DisabilityType.COGNITIVE
    if any(word in command for word in ("ода", "двигат", "мотор", "движен")):
        return DisabilityType.MOTOR
    return None


def _make_response(
    text: str,
    tts: str | None = None,
    session_state: dict[str, Any] | None = None,
    end_session: bool = False,
) -> AliceResponse:
    """Формирует ответ для Алисы.

    Args:
        text: Текст ответа.
        tts: Текст для озвучивания (если отличается от text).
        session_state: Состояние сессии для сохранения.
        end_session: Завершить ли сессию.

    Returns:
        Ответ в формате Яндекс.Диалогов.
    """
    return AliceResponse(
        response={
            "text": text,
            "tts": tts or text,
            "end_session": end_session,
        },
        session_state=session_state or {},
        user_state={},
        application_state={},
        version="1.0",
    )


# ──────────────────────────── Маршрут ─────────────────────────────────


@router.post("/webhook", summary="Вебхук для навыка Алисы")
async def alice_webhook(request: AliceRequest) -> AliceResponse:
    """Точка входа для вебхука от навыка Алисы.

    Принимает запросы в формате Яндекс.Диалогов и возвращает ответы.
    """
    return await _handle_alice_request(request)

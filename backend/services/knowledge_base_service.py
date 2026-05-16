"""
Сервис работы с базой знаний (RAG).
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from backend.models.schemas import (
    DisabilityType,
    KnowledgeHintRequest,
    KnowledgeHintResponse,
    ProfileResponse,
)
from backend.services.profile_service import ProfileService
from backend.utils.rag import add_document_to_knowledge_base, search_knowledge_base
from backend.utils.yandex_api import call_yandex_gpt

logger = logging.getLogger(__name__)


# ──────────────────────────── Начальные данные ────────────────────────

SEED_DOCUMENTS: list[dict[str, str]] = [
    {
        "text": (
            "Чтобы объяснить понятие 'фотосинтез', используй аналогию: "
            "'Представь, что растение — это маленькая фабрика. Оно берет солнечный свет, "
            "как электричество, воду из почвы и углекислый газ из воздуха, как сырье, "
            "и производит из них сахар (свою еду) и кислород, который выделяет в воздух.'"
        ),
        "category": "объяснение_биология",
        "source": "подсказки_для_детей",
    },
    {
        "text": (
            "Если пользователь говорит 'Я не понимаю', не повторяй вопрос. "
            "Вместо этого задай уточняющий вопрос: 'Расскажи, что именно тебе непонятно? "
            "Может быть, слово в вопросе или то, что нужно сделать?' "
            "Предложи помощь: 'Я могу объяснить это слово или разбить вопрос на части. "
            "Что тебе больше поможет?'"
        ),
        "category": "сценарий_поддержки",
        "source": "руководство_педагога",
    },
    {
        "text": (
            "Для пользователей с когнитивными особенностями: разбивай длинные задания "
            "на короткие шаги. Вместо 'Решите уравнение и найдите корни' скажите "
            "'Шаг 1: Перенесите все числа в правую часть. Шаг 2: Вычислите результат. "
            "Шаг 3: Запишите ответ.'"
        ),
        "category": "методика_когнитивные",
        "source": "руководство_адаптация",
    },
    {
        "text": (
            "Для пользователей с нарушениями ОДА: давайте короткие, чёткие инструкции. "
            "Избегайте длинных предложений. Подтверждайте понимание: 'Ты выбрал вариант А. "
            "Записываю ответ. Переходим к следующему?'"
        ),
        "category": "методика_ОДА",
        "source": "руководство_адаптация",
    }
]

_is_seeded: bool = False


class KnowledgeBaseService:
    """Сервис для работы с базой знаний (RAG)."""

    @staticmethod
    async def seed_knowledge_base() -> int:
        """Заполняет базу знаний начальными данными.

        Returns:
            Количество добавленных документов.
        """
        global _is_seeded
        if _is_seeded:
            return 0

        count = 0
        for doc in SEED_DOCUMENTS:
            add_document_to_knowledge_base(
                text=doc["text"],
                metadata={"category": doc["category"], "source": doc["source"]},
            )
            count += 1

        _is_seeded = True
        logger.info(f"База знаний наполнена: {count} документов")
        return count

    @staticmethod
    async def get_hint(request: KnowledgeHintRequest) -> KnowledgeHintResponse:
        """Ищет подсказку в базе знаний на основе запроса пользователя.

        Args:
            request: Запрос подсказки.

        Returns:
            Найденная подсказка.
        """
        # Формируем поисковый запрос
        search_query = request.user_query
        if request.current_question_text:
            search_query = f"{request.user_query} {request.current_question_text}"

        # Ищем в базе знаний
        results = search_knowledge_base(search_query, top_k=3)

        if not results:
            # Если ничего не найдено, генерируем подсказку через GPT
            return await KnowledgeBaseService._generate_hint_with_gpt(request)

        best_result = results[0]
        hint_text = best_result.get("text", "")

        # Если уверенность низкая, дополняем через GPT
        if best_result.get("score", 0) < 0.5:
            gpt_hint = await KnowledgeBaseService._generate_hint_with_gpt(request)
            if gpt_hint.hint_text:
                return gpt_hint

        return KnowledgeHintResponse(
            hint_text=hint_text,
            source=best_result.get("metadata", {}).get("source"),
            confidence=best_result.get("score", 0.0),
        )

    @staticmethod
    async def _generate_hint_with_gpt(request: KnowledgeHintRequest) -> KnowledgeHintResponse:
        """Генерирует подсказку через YandexGPT, если RAG не дал результата.

        Args:
            request: Запрос подсказки.

        Returns:
            Сгенерированная подсказка.
        """
        # Получаем профиль пользователя для персонализации
        profile = await ProfileService.get_profile(request.user_profile_id)
        is_cognitive = False
        disability_info = ""
        if profile:
            disability_info = f"У пользователя тип ОВЗ: {profile.disability_type.value}."
            is_cognitive = profile.disability_type == DisabilityType.COGNITIVE

        context = ""
        if request.current_question_text:
            context = f"Контекст: текущий вопрос теста — «{request.current_question_text}».\n"

        if request.question_options:
            options_text = ", ".join(request.question_options)
            context += f"Варианты ответа: {options_text}.\n"

        if is_cognitive:
            system_prompt = (
                "Дай подсказку одним коротким предложением. "
                "Опиши, что делает правильный ответ, простыми словами. "
                "Без аналогий, без вопросов, без рассуждений. "
                "Примеры хороших подсказок: "
                "'Этот орган помогает тебе вдыхать и выдыхать воздух.' "
                "'Этот газ мы вдыхаем, чтобы жить.' "
                "Не называй правильный ответ прямо. Максимум 15 слов."
                f" {disability_info}"
            )
        else:
            system_prompt = (
                "Дай короткую наводящую подсказку — 1-2 предложения, максимум 25 слов. "
                "Опиши суть правильного ответа или приведи одну простую аналогию. "
                "Не называй правильный ответ прямо. Не задавай вопросов. Не рассуждай."
                f" {disability_info}"
            )

        user_message = f"{context}Запрос пользователя: {request.user_query}"

        try:
            gpt_response = await call_yandex_gpt(
                messages=[{"role": "user", "text": user_message}],
                system_prompt=system_prompt,
                temperature=0.5,
            )
            return KnowledgeHintResponse(
                hint_text=gpt_response,
                source="yandex_gpt",
                confidence=0.7,
            )
        except Exception as e:
            logger.error(f"Ошибка генерации подсказки через GPT: {e}")
            return KnowledgeHintResponse(
                hint_text="К сожалению, не удалось найти подсказку. Попробуйте переформулировать вопрос.",
                source=None,
                confidence=0.0,
            )

    @staticmethod
    async def add_document(text: str, metadata: Optional[dict[str, str]] = None) -> str:
        """Добавляет документ в базу знаний.

        Args:
            text: Текст документа.
            metadata: Метаданные документа.

        Returns:
            Идентификатор добавленного документа.
        """
        return add_document_to_knowledge_base(text, metadata=metadata)

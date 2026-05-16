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
            "При описании изображения с графиком начни с общего описания: "
            "'На изображении показан линейный график, отображающий изменение температуры "
            "воздуха в течение недели.' Затем опиши оси: 'По горизонтальной оси (X) "
            "отложены дни недели, по вертикальной оси (Y) — температура в градусах "
            "Цельсия.' Перечисли ключевые точки: 'Температура была самой низкой в "
            "понедельник (15°C) и самой высокой в пятницу (25°C).'"
        ),
        "category": "методика_слабовидящие",
        "source": "руководство_адаптация",
    },
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
    },
    {
        "text": (
            "Гравитация — это сила, которая притягивает предметы друг к другу. "
            "Представь, что у тебя есть магнит. Он притягивает железные предметы. "
            "Земля работает как огромный магнит — она притягивает всё, что находится "
            "рядом, включая нас. Поэтому мы не улетаем в космос!"
        ),
        "category": "объяснение_физика",
        "source": "подсказки_для_детей",
    },
    {
        "text": (
            "Дробь — это часть целого. Представь пиццу, разрезанную на 4 равных куска. "
            "Если ты съел 1 кусок, ты съел 1/4 пиццы. Число сверху (1) — сколько "
            "кусков ты взял, а число снизу (4) — на сколько кусков разрезана пицца."
        ),
        "category": "объяснение_математика",
        "source": "подсказки_для_детей",
    },
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
        if best_result.get("score", 0) < 0.3:
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
        disability_info = ""
        if profile:
            disability_info = f"У пользователя тип ОВЗ: {profile.disability_type.value}."

        context = ""
        if request.current_question_text:
            context = f"Контекст: текущий вопрос теста — «{request.current_question_text}».\n"

        system_prompt = (
            "Ты — помощник в инклюзивном обучении. Твоя задача — дать простое, "
            "понятное объяснение или подсказку по запросу пользователя. "
            "Используй аналогии из повседневной жизни. "
            f"{disability_info}"
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

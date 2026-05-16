"""
Сервис генерации адаптированного контента.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any, Optional

from backend.models.schemas import DisabilityType
from backend.utils.yandex_api import call_yandex_gpt

logger = logging.getLogger(__name__)

# Системные промпты для адаптации под разные типы ОВЗ
ADAPTATION_PROMPTS: dict[str, str] = {
    DisabilityType.COGNITIVE.value: (
        "Ты — эксперт по инклюзивному образованию. Твоя задача — адаптировать следующий вопрос теста "
        "для пользователя с когнитивными особенностями. "
        "ПРАВИЛА АДАПТАЦИИ:\n"
        "1. Упрости язык: замени сложные слова на простые и знакомые.\n"
        "2. Разбей сложные предложения на короткие (не более 8 слов в предложении).\n"
        "3. Сократи длину текста вопроса и вариантов ответов — убери лишние детали.\n"
        "4. Если понятие сложное, добавь короткую аналогию из повседневной жизни.\n"
        "5. Уменьши количество вариантов ответа до 2–3 (обязательно включи правильный).\n"
        "6. Формулировки должны быть максимально простыми и понятными.\n"
        "Сохрани суть вопроса. Верни результат в формате JSON с полями: "
        "id, text, options, correct_option_index."
    ),
    DisabilityType.VISION.value: (
        "Ты — эксперт по инклюзивному образованию. Твоя задача — адаптировать следующий вопрос теста "
        "для слабовидящего пользователя. Добавь подробное аудио-описание для любых изображений, "
        "графиков и диаграмм. Убери визуальные элементы, которые невозможно озвучить. "
        "Сохрани суть вопроса и варианты ответов. Верни результат в том же формате."
    ),
    DisabilityType.MOTOR.value: (
        "Ты — эксперт по инклюзивному образованию. Твоя задача — адаптировать следующий вопрос теста "
        "для пользователя с нарушениями опорно-двигательного аппарата. Сделай инструкции короткими "
        "и чёткими. Уменьши количество вариантов ответа до двух-трёх, если это возможно. "
        "Сохрани суть вопроса. Верни результат в том же формате."
    ),
}

# Временное in-memory хранилище адаптированных тестов
_adapted_tests_db: dict[str, dict[str, Any]] = {}


class AdaptationService:
    """Сервис для генерации адаптированного контента."""

    @staticmethod
    async def create_adapted_test(
        original_test: dict[str, Any],
        disability_type: DisabilityType,
        *,
        use_gpt: bool = True,
    ) -> dict[str, Any]:
        """Генерирует адаптированную версию теста.

        Args:
            original_test: Исходный тест в структурированном виде.
            disability_type: Тип ОВЗ, для которого адаптируется тест.
            use_gpt: Использовать YandexGPT для адаптации (иначе — шаблонная адаптация).

        Returns:
            Адаптированный тест.
        """
        adapted_id = str(uuid.uuid4())
        system_prompt = ADAPTATION_PROMPTS.get(
            disability_type.value,
            "Адаптируй следующий вопрос теста для более понятного восприятия.",
        )

        adapted_questions = []
        for question in original_test.get("questions", []):
            if use_gpt:
                adapted_question = await AdaptationService._adapt_question_with_gpt(
                    question, system_prompt, disability_type
                )
            else:
                adapted_question = AdaptationService._adapt_question_template(
                    question, disability_type
                )
            adapted_questions.append(adapted_question)

        adapted_test = {
            "id": adapted_id,
            "original_test_id": original_test.get("id", ""),
            "title": f"{original_test.get('title', 'Тест')} (адаптировано: {disability_type.value})",
            "disability_type": disability_type.value,
            "questions": adapted_questions,
        }

        _adapted_tests_db[adapted_id] = adapted_test
        logger.info(f"Создан адаптированный тест: {adapted_id} для ОВЗ: {disability_type.value}")

        return adapted_test

    @staticmethod
    async def _adapt_question_with_gpt(
        question: dict[str, Any],
        system_prompt: str,
        disability_type: DisabilityType,
    ) -> dict[str, Any]:
        """Адаптирует один вопрос с помощью YandexGPT.

        Args:
            question: Исходный вопрос.
            system_prompt: Системный промпт для адаптации.
            disability_type: Тип ОВЗ.

        Returns:
            Адаптированный вопрос.
        """
        question_text = json.dumps(question, ensure_ascii=False)

        try:
            gpt_response = await call_yandex_gpt(
                messages=[{"role": "user", "text": question_text}],
                system_prompt=system_prompt,
                temperature=0.3,
            )

            # Очищаем ответ от markdown-обёрток (```json ... ```)
            cleaned = re.sub(r'^```(?:json)?\s*\n?', '', gpt_response.strip())
            cleaned = re.sub(r'\n?```\s*$', '', cleaned)

            # Пытаемся распарсить ответ GPT как JSON
            try:
                adapted = json.loads(cleaned)
                if isinstance(adapted, dict) and "text" in adapted:
                    return adapted
            except json.JSONDecodeError:
                pass

            # Попытка извлечь JSON из текста (GPT может добавить пояснения)
            json_match = re.search(r'\{[^{}]*"text"[^{}]*\}', cleaned, re.DOTALL)
            if json_match:
                try:
                    adapted = json.loads(json_match.group())
                    if isinstance(adapted, dict) and "text" in adapted:
                        return adapted
                except json.JSONDecodeError:
                    pass

            # Если JSON не найден, но текст не содержит сырого JSON —
            # обновляем только текст вопроса
            adapted_question = dict(question)
            # Не подставляем сырой JSON как текст вопроса
            if not cleaned.strip().startswith('{'):
                adapted_question["text"] = cleaned
            if disability_type == DisabilityType.VISION:
                adapted_question["image_description"] = cleaned
            return adapted_question

        except Exception as e:
            logger.error(f"Ошибка при адаптации вопроса через GPT: {e}")
            return AdaptationService._adapt_question_template(question, disability_type)

    @staticmethod
    def _adapt_question_template(
        question: dict[str, Any],
        disability_type: DisabilityType,
    ) -> dict[str, Any]:
        """Шаблонная адаптация вопроса (без GPT).

        Args:
            question: Исходный вопрос.
            disability_type: Тип ОВЗ.

        Returns:
            Адаптированный вопрос.
        """
        adapted = dict(question)

        if disability_type == DisabilityType.COGNITIVE:
            # Сокращаем количество вариантов ответа до 2–3
            options = question.get("options", [])
            if len(options) > 3:
                correct_idx = question.get("correct_option_index", 0)
                # Берём правильный ответ и ещё 1-2 неправильных
                new_options = [options[correct_idx]]
                incorrect = [i for i in range(len(options)) if i != correct_idx]
                # Добавляем до 2 неправильных вариантов
                for i in incorrect[:2]:
                    new_options.append(options[i])
                adapted["options"] = new_options
                # Правильный ответ теперь всегда первый — переназначаем индекс
                adapted["correct_option_index"] = 0
            # Упрощаем текст: убираем сложные формулировки, добавляем пометку
            text = question.get("text", "")
            # Убираем лишние знаки препинания и упрощаем
            simplified = text.replace("Определите", "Что это").replace("Укажите", "Выберите").replace("Вычислите", "Посчитайте")
            adapted["text"] = f"📌 {simplified}"
        elif disability_type == DisabilityType.VISION:
            # Добавляем описание для изображения
            adapted["image_description"] = "Аудио-описание: " + question.get("text", "")
        elif disability_type == DisabilityType.MOTOR:
            # Оставляем только первые 3 варианта
            if len(question.get("options", [])) > 3:
                correct_idx = question.get("correct_option_index", 0)
                options = question["options"][:3]
                if correct_idx >= 3:
                    options.append(question["options"][correct_idx])
                adapted["options"] = options
                adapted["correct_option_index"] = min(correct_idx, len(options) - 1)

        return adapted

    @staticmethod
    async def get_adapted_test(test_id: str) -> Optional[dict[str, Any]]:
        """Возвращает адаптированный тест по идентификатору."""
        return _adapted_tests_db.get(test_id)

    @staticmethod
    async def list_adapted_tests() -> list[dict[str, Any]]:
        """Возвращает список всех адаптированных тестов."""
        return list(_adapted_tests_db.values())

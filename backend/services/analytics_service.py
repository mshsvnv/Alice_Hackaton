"""
Сервис формирования аналитики и отчётов.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from backend.utils.yandex_api import call_yandex_gpt

logger = logging.getLogger(__name__)

# Временное in-memory хранилище результатов
_results_db: dict[str, dict[str, Any]] = {}


class AnalyticsService:
    """Сервис для формирования отчётов и аналитики."""

    @staticmethod
    async def save_test_result(
        user_profile_id: str,
        test_id: str,
        answers: list[dict[str, Any]],
        score: float,
    ) -> dict[str, Any]:
        """Сохраняет результат прохождения теста.

        Args:
            user_profile_id: Идентификатор пользователя.
            test_id: Идентификатор теста.
            answers: Массив ответов пользователя.
            score: Итоговый балл.

        Returns:
            Сохранённый результат.
        """
        result_id = str(uuid.uuid4())
        result_data = {
            "id": result_id,
            "user_profile_id": user_profile_id,
            "test_id": test_id,
            "answers": answers,
            "score": score,
        }
        _results_db[result_id] = result_data
        logger.info(f"Сохранён результат теста: {result_id}, балл: {score}")
        return result_data

    @staticmethod
    async def get_user_results(user_profile_id: str) -> list[dict[str, Any]]:
        """Возвращает все результаты пользователя.

        Args:
            user_profile_id: Идентификатор пользователя.

        Returns:
            Список результатов.
        """
        return [
            r for r in _results_db.values() if r["user_profile_id"] == user_profile_id
        ]

    @staticmethod
    async def generate_report(user_profile_id: str) -> str:
        """Генерирует персонализированный отчёт для пользователя.

        Args:
            user_profile_id: Идентификатор пользователя.

        Returns:
            Текст отчёта.
        """
        results = await AnalyticsService.get_user_results(user_profile_id)

        if not results:
            return "У вас пока нет результатов прохождения тестов."

        # Формируем сводку для GPT
        summary_lines = []
        for r in results:
            summary_lines.append(
                f"- Тест «{r['test_id']}»: балл {r['score']}/100, "
                f"ответов: {len(r['answers'])}"
            )
        summary = "\n".join(summary_lines)

        system_prompt = (
            "Ты — аналитик в области инклюзивного образования. "
            "На основе результатов тестирования составь краткий, поддерживающий отчёт "
            "для пользователя. Укажи сильные стороны и области для улучшения. "
            "Используй простой и доброжелательный язык."
        )

        user_message = f"Результаты пользователя:\n{summary}"

        try:
            report = await call_yandex_gpt(
                messages=[{"role": "user", "text": user_message}],
                system_prompt=system_prompt,
                temperature=0.4,
            )
            return report
        except Exception as e:
            logger.error(f"Ошибка генерации отчёта через GPT: {e}")
            # Формируем простой отчёт без GPT
            avg_score = sum(r["score"] for r in results) / len(results)
            return (
                f"Вы прошли {len(results)} тест(ов). "
                f"Средний балл: {avg_score:.1f}/100. "
                f"Продолжайте в том же духе!"
            )

    @staticmethod
    async def get_all_results() -> list[dict[str, Any]]:
        """Возвращает все сохранённые результаты."""
        return list(_results_db.values())

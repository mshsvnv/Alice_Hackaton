"""
Маршруты для получения аналитики.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from backend.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Аналитика"])


@router.get("/results/{user_profile_id}", summary="Результаты пользователя")
async def get_user_results(user_profile_id: str) -> list[dict[str, Any]]:
    """Возвращает все результаты тестирования пользователя."""
    return await AnalyticsService.get_user_results(user_profile_id)


@router.get("/report/{user_profile_id}", summary="Сгенерировать отчёт")
async def generate_report(user_profile_id: str) -> dict[str, str]:
    """Генерирует персонализированный отчёт для пользователя."""
    report = await AnalyticsService.generate_report(user_profile_id)
    return {"report": report}


@router.get("/results", summary="Все результаты")
async def get_all_results() -> list[dict[str, Any]]:
    """Возвращает все сохранённые результаты тестирования."""
    return await AnalyticsService.get_all_results()

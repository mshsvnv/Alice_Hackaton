"""
Маршруты для работы с профилями пользователей.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from backend.models.schemas import ProfileResponse
from backend.services.profile_service import ProfileService

router = APIRouter(prefix="/profiles", tags=["Профили"])


@router.get("/", response_model=list[ProfileResponse], summary="Список всех профилей")
async def list_profiles() -> list[ProfileResponse]:
    """Возвращает список всех профилей пользователей."""
    return await ProfileService.list_profiles()


@router.get("/{profile_id}", response_model=ProfileResponse, summary="Получить профиль")
async def get_profile(profile_id: str) -> ProfileResponse:
    """Возвращает профиль пользователя по идентификатору."""
    profile = await ProfileService.get_profile(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Профиль не найден")
    return profile


@router.patch("/{profile_id}", response_model=ProfileResponse, summary="Обновить профиль")
async def update_profile(profile_id: str, update_data: dict[str, Any]) -> ProfileResponse:
    """Обновляет данные профиля пользователя."""
    profile = await ProfileService.update_profile(profile_id, update_data)
    if profile is None:
        raise HTTPException(status_code=404, detail="Профиль не найден")
    return profile


@router.delete("/{profile_id}", summary="Удалить профиль")
async def delete_profile(profile_id: str) -> dict[str, str]:
    """Удаляет профиль пользователя."""
    deleted = await ProfileService.delete_profile(profile_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Профиль не найден")
    return {"status": "deleted", "profile_id": profile_id}

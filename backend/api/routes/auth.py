"""
Маршруты аутентификации.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.models.schemas import ProfileCreate, ProfileResponse
from backend.services.profile_service import ProfileService

router = APIRouter(prefix="/auth", tags=["Аутентификация"])


@router.post("/register", response_model=ProfileResponse, summary="Регистрация нового пользователя")
async def register(profile_data: ProfileCreate) -> ProfileResponse:
    """Регистрирует нового пользователя и создаёт его профиль."""
    profile = await ProfileService.create_profile(profile_data)
    return profile


@router.get("/profile/{profile_id}", response_model=ProfileResponse, summary="Получить профиль пользователя")
async def get_profile(profile_id: str) -> ProfileResponse:
    """Возвращает профиль пользователя по идентификатору."""
    profile = await ProfileService.get_profile(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Профиль не найден")
    return profile

"""
Сервис работы с профилями пользователей.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Optional

from backend.models.schemas import DisabilityType, InteractionMode, ProfileCreate, ProfileResponse

logger = logging.getLogger(__name__)

# Временное in-memory хранилище для прототипа
_profiles_db: dict[str, dict[str, Any]] = {}


class ProfileService:
    """Сервис для управления профилями пользователей."""

    @staticmethod
    async def create_profile(profile_data: ProfileCreate) -> ProfileResponse:
        """Создаёт новый профиль пользователя.

        Args:
            profile_data: Данные для создания профиля.

        Returns:
            Созданный профиль с присвоенным идентификатором.
        """
        profile_id = str(uuid.uuid4())
        profile_dict = {
            "id": profile_id,
            "name": profile_data.name,
            "disability_type": profile_data.disability_type.value,
            "interaction_mode": profile_data.interaction_mode.value,
            "preferences": json.dumps(profile_data.preferences, ensure_ascii=False),
        }
        _profiles_db[profile_id] = profile_dict
        logger.info(f"Создан профиль пользователя: {profile_id} ({profile_data.name})")

        return ProfileResponse(
            id=profile_id,
            name=profile_data.name,
            disability_type=profile_data.disability_type,
            interaction_mode=profile_data.interaction_mode,
            preferences=profile_data.preferences,
        )

    @staticmethod
    async def get_profile(profile_id: str) -> Optional[ProfileResponse]:
        """Возвращает профиль пользователя по идентификатору.

        Args:
            profile_id: Идентификатор профиля.

        Returns:
            Профиль пользователя или None, если не найден.
        """
        profile_dict = _profiles_db.get(profile_id)
        if profile_dict is None:
            return None

        return ProfileResponse(
            id=profile_dict["id"],
            name=profile_dict["name"],
            disability_type=DisabilityType(profile_dict["disability_type"]),
            interaction_mode=InteractionMode(profile_dict["interaction_mode"]),
            preferences=json.loads(profile_dict.get("preferences", "{}")),
        )

    @staticmethod
    async def update_profile(profile_id: str, update_data: dict[str, Any]) -> Optional[ProfileResponse]:
        """Обновляет профиль пользователя.

        Args:
            profile_id: Идентификатор профиля.
            update_data: Поля для обновления.

        Returns:
            Обновлённый профиль или None, если не найден.
        """
        profile_dict = _profiles_db.get(profile_id)
        if profile_dict is None:
            return None

        for key, value in update_data.items():
            if key == "preferences" and isinstance(value, dict):
                profile_dict[key] = json.dumps(value, ensure_ascii=False)
            elif key in ("disability_type", "interaction_mode") and hasattr(value, "value"):
                profile_dict[key] = value.value
            else:
                profile_dict[key] = value

        _profiles_db[profile_id] = profile_dict
        logger.info(f"Обновлён профиль пользователя: {profile_id}")

        return await ProfileService.get_profile(profile_id)

    @staticmethod
    async def delete_profile(profile_id: str) -> bool:
        """Удаляет профиль пользователя.

        Args:
            profile_id: Идентификатор профиля.

        Returns:
            True, если профиль удалён; False, если не найден.
        """
        if profile_id in _profiles_db:
            del _profiles_db[profile_id]
            logger.info(f"Удалён профиль пользователя: {profile_id}")
            return True
        return False

    @staticmethod
    async def list_profiles() -> list[ProfileResponse]:
        """Возвращает список всех профилей."""
        result = []
        for profile_id in _profiles_db:
            profile = await ProfileService.get_profile(profile_id)
            if profile:
                result.append(profile)
        return result

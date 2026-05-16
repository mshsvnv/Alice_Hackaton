"""
Маршруты для работы с базой знаний (подсказки).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter

from backend.models.schemas import KnowledgeHintRequest, KnowledgeHintResponse
from backend.services.knowledge_base_service import KnowledgeBaseService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge", tags=["База знаний"])


@router.post(
    "/hint",
    response_model=KnowledgeHintResponse,
    summary="Получить подсказку из базы знаний",
)
async def get_hint(request: KnowledgeHintRequest) -> KnowledgeHintResponse:
    """Ищет подсказку в базе знаний на основе запроса пользователя.

    Используется голосовым помощником на фронтенде для предоставления
    контекстных подсказок при прохождении теста.
    """
    return await KnowledgeBaseService.get_hint(request)

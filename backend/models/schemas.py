"""
Pydantic-схемы для валидации данных API «Алиса. Доступное Обучение».
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ──────────────────────────── Перечисления ────────────────────────────


class DisabilityType(str, Enum):
    """Тип ограниченных возможностей здоровья."""

    VISION = "vision"  # Слабовидение
    MOTOR = "motor"  # Нарушения ОДА
    COGNITIVE = "cognitive"  # Когнитивные особенности
    NONE = "none"  # Без ОВЗ


class InteractionMode(str, Enum):
    """Предпочтительный способ взаимодействия."""

    VOICE = "voice"
    TEXT = "text"
    BOTH = "both"


# ──────────────────────────── Профиль ─────────────────────────────────


class ProfileCreate(BaseModel):
    """Схема создания профиля пользователя."""

    name: str = Field(..., min_length=1, max_length=200, description="Имя пользователя")
    disability_type: DisabilityType = Field(default=DisabilityType.NONE, description="Тип ОВЗ")
    interaction_mode: InteractionMode = Field(default=InteractionMode.BOTH, description="Способ взаимодействия")
    preferences: dict[str, Any] = Field(default_factory=dict, description="Дополнительные предпочтения")


class ProfileResponse(ProfileCreate):
    """Схема ответа с профилем пользователя."""

    id: str = Field(..., description="Уникальный идентификатор профиля")


# ──────────────────────────── Тест ────────────────────────────────────


class TestQuestion(BaseModel):
    """Один вопрос теста."""

    id: str = Field(..., description="Идентификатор вопроса")
    text: str = Field(..., description="Текст вопроса")
    options: list[str] = Field(..., min_length=2, description="Варианты ответа")
    correct_option_index: int = Field(..., ge=0, description="Индекс правильного ответа")
    image_description: Optional[str] = Field(default=None, description="Аудио-описание изображения (для слабовидящих)")
    audio_description: Optional[str] = Field(default=None, description="Аудио-описание (для слабовидящих)")


class GenerateQuestionsRequest(BaseModel):
    """Запрос на генерацию вопросов из текста конспекта."""

    text: str = Field(..., min_length=10, description="Текст конспекта")
    complexity: str = Field(default="same", pattern="^(same|simple|advanced)$", description="Сложность: same — не менять, simple — упростить, advanced — усложнить")
    count: int = Field(default=5, ge=1, le=10, description="Количество вопросов (1–10)")


class TestCreate(BaseModel):
    """Схема создания теста."""

    title: str = Field(..., min_length=1, max_length=500, description="Название теста")
    author_id: str = Field(..., description="Идентификатор автора")
    disability_type: DisabilityType = Field(default=DisabilityType.NONE, description="Тип ОВЗ для адаптации")
    questions: list[TestQuestion] = Field(..., min_length=1, description="Список вопросов")
    is_public: bool = Field(default=True, description="Публичный тест")


class TestResponse(BaseModel):
    """Схема ответа с тестом."""

    id: str = Field(..., description="Идентификатор теста")
    title: str = Field(..., description="Название теста")
    author_id: str = Field(..., description="Идентификатор автора")
    disability_type: DisabilityType = Field(..., description="Тип ОВЗ")
    questions: list[TestQuestion] = Field(..., description="Список вопросов")
    is_public: bool = Field(..., description="Публичный тест")
    share_link: Optional[str] = Field(default=None, description="Ссылка для общего доступа")
    created_at: Optional[str] = Field(default=None, description="Дата создания")


class TestListItem(BaseModel):
    """Краткая информация о тесте для списка."""

    id: str = Field(..., description="Идентификатор теста")
    title: str = Field(..., description="Название теста")
    author_id: str = Field(..., description="Идентификатор автора")
    disability_type: DisabilityType = Field(..., description="Тип ОВЗ")
    is_public: bool = Field(..., description="Публичный тест")
    share_link: Optional[str] = Field(default=None, description="Ссылка для общего доступа")
    questions_count: int = Field(..., description="Количество вопросов")
    created_at: Optional[str] = Field(default=None, description="Дата создания")


class TestResultCreate(BaseModel):
    """Схема сохранения результата теста."""

    user_profile_id: str = Field(..., description="Идентификатор пользователя")
    test_id: str = Field(..., description="Идентификатор пройденного теста")
    answers: list[dict[str, Any]] = Field(..., description="Массив ответов пользователя")
    score: float = Field(..., ge=0, le=100, description="Итоговый балл (0–100)")


class TestResultResponse(TestResultCreate):
    """Схема ответа с результатом теста."""

    id: str = Field(..., description="Идентификатор результата")


# ──────────────────────────── База знаний ─────────────────────────────


class KnowledgeHintRequest(BaseModel):
    """Запрос подсказки из базы знаний."""

    user_query: str = Field(..., min_length=1, description="Текст запроса пользователя")
    user_profile_id: str = Field(..., description="Идентификатор профиля пользователя")
    current_question_text: Optional[str] = Field(default=None, description="Текст текущего вопроса теста")
    question_options: Optional[list[str]] = Field(default=None, description="Варианты ответа на вопрос")


class KnowledgeHintResponse(BaseModel):
    """Ответ с подсказкой из базы знаний."""

    hint_text: str = Field(..., description="Текст подсказки")
    source: Optional[str] = Field(default=None, description="Источник подсказки")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Уверенность в релевантности")


# ──────────────────────────── Алиса (вебхук) ──────────────────────────


class AliceRequest(BaseModel):
    """Модель входящего запроса от навыка Алисы.

    Соответствует формату Яндекс.Диалогов.
    Ссылка: https://yandex.ru/dev/dialogs/alice/doc/protocol.html
    """

    meta: dict[str, Any] = Field(default_factory=dict)
    request: dict[str, Any] = Field(default_factory=dict)
    session: dict[str, Any] = Field(default_factory=dict)
    state: dict[str, Any] = Field(default_factory=dict)
    version: str = Field(default="1.0")


class AliceResponse(BaseModel):
    """Модель ответа навыка Алисы."""

    response: dict[str, Any]
    session_state: dict[str, Any] = Field(default_factory=dict, alias="session_state")
    user_state: dict[str, Any] = Field(default_factory=dict, alias="user_state")
    application_state: dict[str, Any] = Field(default_factory=dict, alias="application_state")
    version: str = Field(default="1.0")

    model_config = {"populate_by_name": True}

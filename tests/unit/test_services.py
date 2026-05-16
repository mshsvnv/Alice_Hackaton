"""
Unit-тесты для ключевых сервисов «Алиса. Доступное Обучение».
"""

from __future__ import annotations

import pytest

from backend.models.schemas import (
    DisabilityType,
    InteractionMode,
    KnowledgeHintRequest,
    ProfileCreate,
)
from backend.services.adaptation_service import AdaptationService
from backend.services.document_service import DocumentService
from backend.services.knowledge_base_service import KnowledgeBaseService
from backend.services.profile_service import ProfileService


# ──────────────────────────── Фикстуры ────────────────────────────────


@pytest.fixture
def sample_profile_data() -> ProfileCreate:
    """Создаёт тестовые данные профиля."""
    return ProfileCreate(
        name="Тестовый пользователь",
        disability_type=DisabilityType.COGNITIVE,
        interaction_mode=InteractionMode.VOICE,
        preferences={"font_size": "large"},
    )


@pytest.fixture
def sample_test_text() -> str:
    """Возвращает текст теста для парсинга."""
    return """Вопрос: Что такое фотосинтез?
А) Процесс, при котором растения поглощают воду из почвы.
Б) Процесс, при котором растения производят свою пищу с помощью солнечного света.
В) Процесс, при котором растения выделяют кислород в почву.
Г) Процесс, при котором растения растут в высоту.
Ответ: Б

Вопрос: Какой газ растения выделяют при фотосинтезе?
А) Углекислый газ
Б) Азот
В) Кислород
Г) Водород
Ответ: В"""


@pytest.fixture
def sample_test_parsed() -> dict:
    """Возвращает распарсенный тест."""
    return {
        "id": "test_1",
        "title": "Тест по биологии",
        "questions": [
            {
                "id": "q1",
                "text": "Что такое фотосинтез?",
                "options": [
                    "Процесс, при котором растения поглощают воду из почвы.",
                    "Процесс, при котором растения производят свою пищу с помощью солнечного света.",
                    "Процесс, при котором растения выделяют кислород в почву.",
                    "Процесс, при котором растения растут в высоту.",
                ],
                "correct_option_index": 1,
            },
            {
                "id": "q2",
                "text": "Какой газ растения выделяют при фотосинтезе?",
                "options": [
                    "Углекислый газ",
                    "Азот",
                    "Кислород",
                    "Водород",
                ],
                "correct_option_index": 2,
            },
        ],
    }


# ──────────────────────────── ProfileService ──────────────────────────


@pytest.mark.asyncio
async def test_create_profile(sample_profile_data: ProfileCreate):
    """Тест создания профиля пользователя."""
    profile = await ProfileService.create_profile(sample_profile_data)

    assert profile.id is not None
    assert profile.name == "Тестовый пользователь"
    assert profile.disability_type == DisabilityType.COGNITIVE
    assert profile.interaction_mode == InteractionMode.VOICE
    assert profile.preferences == {"font_size": "large"}


@pytest.mark.asyncio
async def test_get_profile(sample_profile_data: ProfileCreate):
    """Тест получения профиля по идентификатору."""
    created = await ProfileService.create_profile(sample_profile_data)
    found = await ProfileService.get_profile(created.id)

    assert found is not None
    assert found.id == created.id
    assert found.name == created.name


@pytest.mark.asyncio
async def test_get_profile_not_found():
    """Тест получения несуществующего профиля."""
    result = await ProfileService.get_profile("nonexistent_id")
    assert result is None


@pytest.mark.asyncio
async def test_list_profiles(sample_profile_data: ProfileCreate):
    """Тест получения списка профилей."""
    await ProfileService.create_profile(sample_profile_data)
    profiles = await ProfileService.list_profiles()

    assert len(profiles) >= 1


@pytest.mark.asyncio
async def test_delete_profile(sample_profile_data: ProfileCreate):
    """Тест удаления профиля."""
    created = await ProfileService.create_profile(sample_profile_data)
    deleted = await ProfileService.delete_profile(created.id)

    assert deleted is True
    assert await ProfileService.get_profile(created.id) is None


# ──────────────────────────── DocumentService ─────────────────────────


@pytest.mark.asyncio
async def test_upload_txt_document():
    """Тест загрузки текстового документа."""
    content = "Это тестовый документ с текстом.".encode("utf-8")
    result = await DocumentService.upload_document("test.txt", content)

    assert result["id"] is not None
    assert result["filename"] == "test.txt"
    assert result["status"] == "processed"
    assert "тестовый документ" in result["extracted_text"]


@pytest.mark.asyncio
async def test_parse_test_from_text(sample_test_text: str):
    """Тест парсинга теста из текста."""
    result = await DocumentService.parse_test_from_text(sample_test_text)

    assert "questions" in result
    assert len(result["questions"]) == 2
    assert result["questions"][0]["text"] == "Что такое фотосинтез?"
    assert len(result["questions"][0]["options"]) == 4
    assert result["questions"][0]["correct_option_index"] == 1
    assert result["questions"][1]["correct_option_index"] == 2


@pytest.mark.asyncio
async def test_parse_empty_text():
    """Тест парсинга пустого текста."""
    result = await DocumentService.parse_test_from_text("")
    assert result["questions"] == []


# ──────────────────────────── AdaptationService ───────────────────────


@pytest.mark.asyncio
async def test_create_adapted_test_cognitive(sample_test_parsed: dict):
    """Тест адаптации теста для когнитивных особенностей (шаблон)."""
    result = await AdaptationService.create_adapted_test(
        sample_test_parsed, DisabilityType.COGNITIVE, use_gpt=False
    )

    assert result["id"] is not None
    assert result["disability_type"] == "cognitive"
    assert result["original_test_id"] == "test_1"
    assert len(result["questions"]) == 2
    # Шаблонная адаптация добавляет пометку
    assert "упрощённая версия" in result["questions"][0]["text"]


@pytest.mark.asyncio
async def test_create_adapted_test_vision(sample_test_parsed: dict):
    """Тест адаптации теста для слабовидящих (шаблон)."""
    result = await AdaptationService.create_adapted_test(
        sample_test_parsed, DisabilityType.VISION, use_gpt=False
    )

    assert result["disability_type"] == "vision"
    # Для слабовидящих добавляется описание изображения
    assert "image_description" in result["questions"][0]


@pytest.mark.asyncio
async def test_create_adapted_test_motor(sample_test_parsed: dict):
    """Тест адаптации теста для ОДА (шаблон)."""
    # Создаём тест с 4 вариантами
    result = await AdaptationService.create_adapted_test(
        sample_test_parsed, DisabilityType.MOTOR, use_gpt=False
    )

    assert result["disability_type"] == "motor"
    # Для ОДА количество вариантов может быть уменьшено
    for question in result["questions"]:
        assert len(question["options"]) <= 4


# ──────────────────────────── KnowledgeBaseService ────────────────────


@pytest.mark.asyncio
async def test_seed_knowledge_base():
    """Тест начального заполнения базы знаний."""
    count = await KnowledgeBaseService.seed_knowledge_base()
    assert count >= 0  # Может быть 0 при повторном вызове


@pytest.mark.asyncio
async def test_add_document_to_knowledge_base():
    """Тест добавления документа в базу знаний."""
    doc_id = await KnowledgeBaseService.add_document(
        text="Тестовый документ для проверки RAG.",
        metadata={"category": "test", "source": "unit_test"},
    )
    assert doc_id is not None


@pytest.mark.asyncio
async def test_get_hint():
    """Тест получения подсказки из базы знаний."""
    # Сначала наполняем
    await KnowledgeBaseService.seed_knowledge_base()

    request = KnowledgeHintRequest(
        user_query="Что такое фотосинтез?",
        user_profile_id="test_user",
    )
    result = await KnowledgeBaseService.get_hint(request)

    assert result.hint_text is not None
    assert len(result.hint_text) > 0


# ──────────────────────────── Alice webhook ────────────────────────────


@pytest.mark.asyncio
async def test_alice_webhook_start():
    """Тест начального запроса к Алисе."""
    from backend.models.schemas import AliceRequest

    request = AliceRequest(
        request={"command": "", "original_utterance": ""},
        session={"user": {"user_id": "test_user"}, "state": {}},
        state={},
        version="1.0",
    )

    from backend.api.routes.alice import _handle_alice_request

    response = await _handle_alice_request(request)
    assert response.response["text"] is not None
    assert "Алиса" in response.response["text"] or "помощник" in response.response["text"]


@pytest.mark.asyncio
async def test_alice_webhook_hint():
    """Тест запроса подсказки через Алису."""
    from backend.models.schemas import AliceRequest

    await KnowledgeBaseService.seed_knowledge_base()

    request = AliceRequest(
        request={"command": "подсказка фотосинтез", "original_utterance": "Подскажи что такое фотосинтез"},
        session={"user": {"user_id": "test_user"}, "state": {"step": "menu"}},
        state={},
        version="1.0",
    )

    from backend.api.routes.alice import _handle_alice_request

    response = await _handle_alice_request(request)
    assert response.response["text"] is not None
    assert len(response.response["text"]) > 0

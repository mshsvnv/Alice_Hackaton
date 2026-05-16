"""
Маршруты для управления тестами: создание, прохождение, обмен.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query

from backend.models.schemas import (
    DisabilityType,
    TestCreate,
    TestListItem,
    TestResponse,
    TestResultCreate,
    TestResultResponse,
)
from backend.services.adaptation_service import AdaptationService
from backend.services.document_service import DocumentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tests", tags=["Тесты"])

# In-memory хранилище тестов
_tests_db: dict[str, dict[str, Any]] = {}

# In-memory хранилище результатов
_results_db: list[dict[str, Any]] = []


def _generate_share_link(test_id: str) -> str:
    """Генерирует короткую ссылку для обмена тестом."""
    short = uuid.uuid4().hex[:8]
    return f"test-{short}"


def _test_to_response(test: dict[str, Any]) -> TestResponse:
    """Конвертирует внутреннее представление теста в ответ API."""
    return TestResponse(
        id=test["id"],
        title=test["title"],
        author_id=test["author_id"],
        disability_type=DisabilityType(test.get("disability_type", "none")),
        questions=test.get("questions", []),
        is_public=test.get("is_public", True),
        share_link=test.get("share_link"),
        created_at=test.get("created_at"),
    )


def _test_to_list_item(test: dict[str, Any]) -> TestListItem:
    """Конвертирует тест в краткий элемент списка."""
    questions = test.get("questions", [])
    return TestListItem(
        id=test["id"],
        title=test["title"],
        author_id=test["author_id"],
        disability_type=DisabilityType(test.get("disability_type", "none")),
        is_public=test.get("is_public", True),
        share_link=test.get("share_link"),
        questions_count=len(questions),
        created_at=test.get("created_at"),
    )


@router.post("/create", response_model=TestResponse, summary="Создать тест")
async def create_test(data: TestCreate) -> TestResponse:
    """Создаёт новый тест. Если указан тип ОВЗ, автоматически адаптирует вопросы.

    Тест становится публичным и доступным по ссылке.
    """
    test_id = str(uuid.uuid4())
    share_link = _generate_share_link(test_id)

    questions = [q.model_dump() for q in data.questions]

    # Если указан тип ОВЗ (не none, не vision, не motor), адаптируем вопросы
    # Для слабовидения и нарушений ОДА адаптация не нужна — голосовой помощник
    # озвучивает вопросы и audio_description без изменения текста
    if (data.disability_type != DisabilityType.NONE
        and data.disability_type != DisabilityType.VISION
        and data.disability_type != DisabilityType.MOTOR):
        original_test = {"id": test_id, "title": data.title, "questions": questions}
        adapted = await AdaptationService.create_adapted_test(
            original_test, data.disability_type, use_gpt=True
        )
        questions = adapted.get("questions", questions)

    test = {
        "id": test_id,
        "title": data.title,
        "author_id": data.author_id,
        "disability_type": data.disability_type.value,
        "questions": questions,
        "is_public": data.is_public,
        "share_link": share_link,
        "created_at": None,
    }

    _tests_db[test_id] = test
    logger.info(f"Создан тест: {test_id} ({data.title}), ОВЗ: {data.disability_type.value}")

    return _test_to_response(test)


@router.post("/create-from-document", response_model=TestResponse, summary="Создать тест из документа")
async def create_test_from_document(
    document_id: str = Query(..., description="ID загруженного документа"),
    title: str = Query(..., description="Название теста"),
    author_id: str = Query(..., description="ID автора"),
    disability_type: DisabilityType = Query(default=DisabilityType.NONE, description="Тип ОВЗ для адаптации"),
    is_public: bool = Query(default=True, description="Публичный тест"),
) -> TestResponse:
    """Создаёт тест из загруженного документа с автоматической адаптацией."""
    doc = await DocumentService.get_document(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Документ не найден")

    parsed = await DocumentService.parse_test_from_text(doc.get("extracted_text", ""))
    if not parsed.get("questions"):
        raise HTTPException(status_code=400, detail="Не удалось распознать вопросы в документе")

    test_id = str(uuid.uuid4())
    share_link = _generate_share_link(test_id)
    questions = parsed.get("questions", [])

    # Адаптируем если указан тип ОВЗ (кроме vision и motor — для слабовидения
    # и нарушений ОДА адаптация вопросов не нужна, голосовой помощник озвучивает как есть)
    if (disability_type != DisabilityType.NONE
        and disability_type != DisabilityType.VISION
        and disability_type != DisabilityType.MOTOR):
        original_test = {"id": test_id, "title": title, "questions": questions}
        adapted = await AdaptationService.create_adapted_test(
            original_test, disability_type, use_gpt=True
        )
        questions = adapted.get("questions", questions)

    test = {
        "id": test_id,
        "title": title,
        "author_id": author_id,
        "disability_type": disability_type.value,
        "questions": questions,
        "is_public": is_public,
        "share_link": share_link,
        "created_at": None,
    }

    _tests_db[test_id] = test
    logger.info(f"Создан тест из документа {document_id}: {test_id}")

    return _test_to_response(test)


@router.post("/create-from-text", response_model=TestResponse, summary="Создать тест из текста")
async def create_test_from_text(
    text: str = Query(..., description="Текст теста"),
    title: str = Query(..., description="Название теста"),
    author_id: str = Query(..., description="ID автора"),
    disability_type: DisabilityType = Query(default=DisabilityType.NONE, description="Тип ОВЗ для адаптации"),
    is_public: bool = Query(default=True, description="Публичный тест"),
) -> TestResponse:
    """Парсит текст и создаёт тест с автоматической адаптацией."""
    parsed = await DocumentService.parse_test_from_text(text)
    if not parsed.get("questions"):
        raise HTTPException(status_code=400, detail="Не удалось распознать вопросы в тексте")

    test_id = str(uuid.uuid4())
    share_link = _generate_share_link(test_id)
    questions = parsed.get("questions", [])

    # Адаптируем если указан тип ОВЗ (кроме vision и motor — для слабовидения
    # и нарушений ОДА адаптация вопросов не нужна, голосовой помощник озвучивает как есть)
    if (disability_type != DisabilityType.NONE
        and disability_type != DisabilityType.VISION
        and disability_type != DisabilityType.MOTOR):
        original_test = {"id": test_id, "title": title, "questions": questions}
        adapted = await AdaptationService.create_adapted_test(
            original_test, disability_type, use_gpt=True
        )
        questions = adapted.get("questions", questions)

    test = {
        "id": test_id,
        "title": title,
        "author_id": author_id,
        "disability_type": disability_type.value,
        "questions": questions,
        "is_public": is_public,
        "share_link": share_link,
        "created_at": None,
    }

    _tests_db[test_id] = test
    logger.info(f"Создан тест из текста: {test_id}")

    return _test_to_response(test)


@router.get("/public", response_model=list[TestListItem], summary="Список публичных тестов")
async def list_public_tests() -> list[TestListItem]:
    """Возвращает все публичные тесты."""
    return [
        _test_to_list_item(t)
        for t in _tests_db.values()
        if t.get("is_public", True)
    ]


@router.get("/by-author/{author_id}", response_model=list[TestListItem], summary="Тесты автора")
async def list_author_tests(author_id: str) -> list[TestListItem]:
    """Возвращает все тесты указанного автора."""
    return [
        _test_to_list_item(t)
        for t in _tests_db.values()
        if t.get("author_id") == author_id
    ]


@router.get("/{test_id}", response_model=TestResponse, summary="Получить тест по ID")
async def get_test(test_id: str) -> TestResponse:
    """Возвращает тест по идентификатору."""
    test = _tests_db.get(test_id)
    if test is None:
        raise HTTPException(status_code=404, detail="Тест не найден")
    return _test_to_response(test)


@router.get("/share/{share_link}", response_model=TestResponse, summary="Получить тест по ссылке")
async def get_test_by_share_link(share_link: str) -> TestResponse:
    """Возвращает тест по ссылке для общего доступа."""
    for test in _tests_db.values():
        if test.get("share_link") == share_link:
            return _test_to_response(test)
    raise HTTPException(status_code=404, detail="Тест по ссылке не найден")


@router.post("/results", response_model=TestResultResponse, summary="Сохранить результат теста")
async def save_test_result(result_data: TestResultCreate) -> TestResultResponse:
    """Сохраняет результат прохождения теста."""
    # Проверяем, что тест существует
    if result_data.test_id not in _tests_db:
        raise HTTPException(status_code=404, detail="Тест не найден")

    result_id = str(uuid.uuid4())
    result = {
        "id": result_id,
        "user_profile_id": result_data.user_profile_id,
        "test_id": result_data.test_id,
        "answers": result_data.answers,
        "score": result_data.score,
    }

    _results_db.append(result)
    logger.info(f"Сохранён результат теста {result_data.test_id}: балл {result_data.score}")

    return TestResultResponse(
        id=result_id,
        user_profile_id=result_data.user_profile_id,
        test_id=result_data.test_id,
        answers=result_data.answers,
        score=result_data.score,
    )


@router.get("/results/{user_profile_id}", response_model=list[TestResultResponse], summary="Результаты пользователя")
async def get_user_results(user_profile_id: str) -> list[TestResultResponse]:
    """Возвращает все результаты тестирования пользователя."""
    results = [r for r in _results_db if r.get("user_profile_id") == user_profile_id]
    return [
        TestResultResponse(
            id=r["id"],
            user_profile_id=r["user_profile_id"],
            test_id=r["test_id"],
            answers=r["answers"],
            score=r["score"],
        )
        for r in results
    ]

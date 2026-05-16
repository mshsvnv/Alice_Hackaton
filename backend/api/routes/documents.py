"""
Маршруты для загрузки и обработки документов.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, File, HTTPException, UploadFile

from backend.models.schemas import GenerateQuestionsRequest
from backend.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["Документы"])


@router.post("/upload", summary="Загрузить документ")
async def upload_document(file: UploadFile = File(...)) -> dict[str, Any]:
    """Загружает документ (PDF, DOCX, TXT, изображение) и извлекает текст."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Имя файла не указано")

    content = await file.read()
    result = await DocumentService.upload_document(file.filename, content)
    return result


@router.get("/", summary="Список документов")
async def list_documents() -> list[dict[str, Any]]:
    """Возвращает список всех загруженных документов."""
    return await DocumentService.list_documents()


@router.get("/{doc_id}", summary="Получить документ")
async def get_document(doc_id: str) -> dict[str, Any]:
    """Возвращает информацию о документе по идентификатору."""
    doc = await DocumentService.get_document(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Документ не найден")
    return doc


@router.post("/parse-test", summary="Парсинг теста из текста")
async def parse_test(text: str = Body(..., embed=True)) -> dict[str, Any]:
    """Парсит структуру теста из переданного текста."""
    if not text.strip():
        raise HTTPException(status_code=400, detail="Текст не может быть пустым")
    return await DocumentService.parse_test_from_text(text)


@router.post("/generate-questions", summary="Генерация вопросов из конспекта")
async def generate_questions(data: GenerateQuestionsRequest) -> dict[str, Any]:
    """Генерирует вопросы из текста конспекта с помощью YandexGPT.

    Параметры:
    - text: текст конспекта (минимум 10 символов)
    - complexity: simple (упростить) или advanced (усложнить)
    - count: количество вопросов (1–10, по умолчанию 5)
    """
    try:
        return await DocumentService.generate_questions(
            data.text, complexity=data.complexity, count=data.count,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

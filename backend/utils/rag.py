"""
Утилиты для работы с векторной базой данных (Qdrant) и RAG.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, PointStruct, VectorParams
except ImportError:
    raise ImportError(
        "qdrant-client не установлен. Установите его: pip install qdrant-client. "
        "Qdrant обязателен для работы приложения."
    )


# ──────────────────────────── Инициализация ───────────────────────────


def get_qdrant_client() -> Any:
    """Возвращает клиент Qdrant. Выбрасывает ошибку при недоступности."""
    try:
        client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY or None)
        return client
    except Exception as e:
        raise RuntimeError(
            f"Не удалось подключиться к Qdrant по адресу {settings.QDRANT_URL}: {e}. "
            "Убедитесь, что Qdrant запущен и доступен."
        ) from e


def ensure_collection_exists(client: Any) -> None:
    """Создаёт коллекцию в Qdrant, если она не существует."""
    try:
        collections = client.get_collections().collections
        collection_names = [c.name for c in collections]
        if settings.QDRANT_COLLECTION_NAME not in collection_names:
            client.create_collection(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )
            logger.info(f"Коллекция '{settings.QDRANT_COLLECTION_NAME}' создана")
    except Exception as e:
        logger.error(f"Ошибка при создании коллекции: {e}")


# ──────────────────────────── Простая векторизация ────────────────────


def simple_hash_vector(text: str, size: int = 384) -> list[float]:
    """Простая хеш-векторизация для прототипа (без ML-модели).

    В реальном проекте следует использовать модель эмбеддингов,
    например sentence-transformers или Yandex Embeddings API.

    Args:
        text: Текст для векторизации.
        size: Размерность вектора.

    Returns:
        Вектор фиксированной размерности.
    """
    import hashlib

    hash_obj = hashlib.sha256(text.encode("utf-8"))
    hash_bytes = hash_obj.digest()

    vector = []
    for i in range(size):
        byte_val = hash_bytes[i % len(hash_bytes)]
        # Нормализуем к диапазону [-1, 1]
        vector.append((byte_val / 128.0) - 1.0)

    # Нормализуем вектор
    norm = sum(x * x for x in vector) ** 0.5
    if norm > 0:
        vector = [x / norm for x in vector]

    return vector


# ──────────────────────────── Операции с документами ──────────────────


def add_document_to_knowledge_base(
    text: str,
    metadata: Optional[dict[str, Any]] = None,
    doc_id: Optional[str] = None,
) -> str:
    """Добавляет документ (чанк) в векторную базу знаний.

    Args:
        text: Текст документа.
        metadata: Метаданные документа.
        doc_id: Идентификатор (генерируется, если не указан).

    Returns:
        Идентификатор добавленного документа.

    Raises:
        RuntimeError: Если Qdrant недоступен.
    """
    if doc_id is None:
        doc_id = str(uuid.uuid4())

    vector = simple_hash_vector(text)

    client = get_qdrant_client()
    ensure_collection_exists(client)
    try:
        client.upsert(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            points=[
                PointStruct(
                    id=doc_id,
                    vector=vector,
                    payload={"text": text, **(metadata or {})},
                )
            ],
        )
        logger.info(f"Документ {doc_id} добавлен в Qdrant")
    except Exception as e:
        raise RuntimeError(f"Ошибка при добавлении документа в Qdrant: {e}") from e

    return doc_id


def search_knowledge_base(
    query: str,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    """Ищет релевантные документы в базе знаний.

    Args:
        query: Поисковый запрос.
        top_k: Количество возвращаемых результатов.

    Returns:
        Список найденных документов с метаданными и оценкой релевантности.

    Raises:
        RuntimeError: Если Qdrant недоступен.
    """
    client = get_qdrant_client()
    try:
        query_vector = simple_hash_vector(query)

        # Поддержка разных версий qdrant-client:
        # >= 1.12 — метод query_points, < 1.12 — метод search
        if hasattr(client, "query_points"):
            response = client.query_points(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                query=query_vector,
                limit=top_k,
            )
            results = response.points if hasattr(response, "points") else response
        elif hasattr(client, "search"):
            results = client.search(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                query_vector=query_vector,
                limit=top_k,
            )
        else:
            raise RuntimeError(
                "Qdrant client не поддерживает ни search, ни query_points. "
                "Обновите qdrant-client: pip install 'qdrant-client>=1.9.0'"
            )

        return [
            {
                "id": str(hit.id),
                "text": hit.payload.get("text", ""),
                "score": hit.score,
                "metadata": {k: v for k, v in hit.payload.items() if k != "text"},
            }
            for hit in results
        ]
    except Exception as e:
        raise RuntimeError(f"Ошибка при поиске в Qdrant: {e}") from e



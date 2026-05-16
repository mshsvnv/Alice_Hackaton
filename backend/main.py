"""
Точка входа приложения «Алиса. Доступное Обучение».

Инициализирует FastAPI-сервер, подключает маршруты и запускает
начальное заполнение базы знаний.

При старте выполняется строгая проверка всех зависимостей:
- Qdrant (векторная БД) должен быть доступен
- Yandex API (API-ключ и Folder ID) должен быть настроен
- Алиса (Skill ID и OAuth Token) должна быть настроена

Если любая зависимость недоступна — приложение завершается с ошибкой.
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import alice, auth, documents, knowledge, profile, tests, voice
from backend.config import get_settings
from backend.services.knowledge_base_service import KnowledgeBaseService
from backend.utils.rag import get_qdrant_client
from backend.utils.yandex_api import call_yandex_gpt

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


# ──────────────────────────── Проверка зависимостей ────────────────────


async def _check_qdrant(max_retries: int = 10, retry_delay: float = 3.0) -> None:
    """Проверяет доступность Qdrant с ретраями. Завершает приложение при ошибке."""
    import asyncio

    logger.info("Проверка подключения к Qdrant...")
    for attempt in range(1, max_retries + 1):
        try:
            client = get_qdrant_client()
            collections = client.get_collections().collections
            logger.info(f"✓ Qdrant доступен, коллекций: {len(collections)}")
            return
        except Exception as e:
            if attempt < max_retries:
                logger.warning(f"  Попытка {attempt}/{max_retries} — Qdrant недоступен: {e}")
                logger.warning(f"  Повторная попытка через {retry_delay:.0f}с...")
                await asyncio.sleep(retry_delay)
            else:
                logger.critical(f"✗ Qdrant недоступен после {max_retries} попыток: {e}")
                logger.critical("  Убедитесь, что Qdrant запущен (docker compose up qdrant) и QDRANT_URL указан верно.")
                sys.exit(1)


async def _check_yandex_api() -> None:
    """Проверяет доступность Yandex API. Завершает приложение при ошибке."""
    logger.info("Проверка доступности Yandex API...")
    if not settings.YANDEX_API_KEY:
        logger.critical("✗ YANDEX_API_KEY не задан в переменных окружения")
        logger.critical("  Установите YANDEX_API_KEY в .env файле (получите в Yandex Cloud Console).")
        sys.exit(1)
    if not settings.YANDEX_FOLDER_ID:
        logger.critical("✗ YANDEX_FOLDER_ID не задан в переменных окружения")
        logger.critical("  Установите YANDEX_FOLDER_ID в .env файле (ID каталога в Yandex Cloud).")
        sys.exit(1)
    try:
        test_response = await call_yandex_gpt(
            messages=[{"role": "user", "text": "Проверка"}],
            max_tokens=5,
        )
        logger.info(f"✓ Yandex API доступен, ответ: {test_response[:50]}...")
    except Exception as e:
        logger.critical(f"✗ Yandex API недоступен: {e}")
        logger.critical("  Проверьте корректность YANDEX_API_KEY и YANDEX_FOLDER_ID.")
        sys.exit(1)


def _check_alice_config() -> None:
    """Проверяет конфигурацию интеграции с Алисой (опционально)."""
    logger.info("Проверка конфигурации Алисы...")
    if not settings.ALICE_SKILL_ID or not settings.ALICE_OAUTH_TOKEN:
        logger.warning("⚠ ALICE_SKILL_ID и/или ALICE_OAUTH_TOKEN не заданы")
        logger.warning("  Вебхук Алисы будет доступен, но управление навыком через API — нет.")
        logger.warning("  Для полной интеграции задайте ALICE_SKILL_ID и ALICE_OAUTH_TOKEN в .env файле.")
    else:
        logger.info("✓ Конфигурация Алисы проверена")


# ──────────────────────────── Lifespan ────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения."""
    logger.info("══════════════════════════════════════════════════════")
    logger.info("  Запуск приложения «Алиса. Доступное Обучение»")
    logger.info("══════════════════════════════════════════════════════")

    # Строгая проверка всех зависимостей
    await _check_qdrant()
    await _check_yandex_api()
    _check_alice_config()

    logger.info("✓ Все зависимости проверены и доступны")

    # Наполняем базу знаний
    count = await KnowledgeBaseService.seed_knowledge_base()
    logger.info(f"База знаний наполнена: {count} документов")
    logger.info("══════════════════════════════════════════════════════")
    logger.info("  Приложение запущено и готово к работе")
    logger.info("══════════════════════════════════════════════════════")
    yield

    # При завершении
    logger.info("Остановка приложения")


# ──────────────────────────── Приложение ──────────────────────────────


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Бэкенд платформы «Алиса. Доступное Обучение» — "
        "инклюзивная образовательная платформа с голосовым интерфейсом Алисы."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────── Маршруты ────────────────────────────────

app.include_router(alice.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(profile.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(tests.router, prefix="/api/v1")
app.include_router(voice.router, prefix="/api/v1")
app.include_router(knowledge.router, prefix="/api/v1")


# ──────────────────────────── Health check ────────────────────────────


@app.get("/", tags=["Health"])
async def root() -> dict[str, str]:
    """Корневой эндпоинт для проверки работоспособности."""
    return {
        "service": settings.APP_NAME,
        "status": "ok",
        "version": "0.1.0",
    }


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Эндпоинт для проверки здоровья сервиса и его зависимостей."""
    checks: dict[str, str] = {"status": "healthy"}

    # Проверяем Qdrant
    try:
        client = get_qdrant_client()
        client.get_collections()
        checks["qdrant"] = "ok"
    except Exception:
        checks["qdrant"] = "error"
        checks["status"] = "unhealthy"

    # Проверяем Yandex API
    if not settings.YANDEX_API_KEY or not settings.YANDEX_FOLDER_ID:
        checks["yandex_api"] = "not_configured"
        checks["status"] = "unhealthy"
    else:
        checks["yandex_api"] = "ok"

    # Проверяем Алису (опционально)
    if not settings.ALICE_SKILL_ID or not settings.ALICE_OAUTH_TOKEN:
        checks["alice"] = "not_configured"
    else:
        checks["alice"] = "ok"

    return checks

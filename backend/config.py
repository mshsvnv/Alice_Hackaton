"""
Конфигурация приложения «Алиса. Доступное Обучение».
Загружает переменные окружения и предоставляет настройки для всех сервисов.
"""

import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения, загружаемые из .env файла."""

    # --- Общие ---
    APP_NAME: str = "Алиса. Доступное Обучение"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # --- База данных ---
    DATABASE_URL: str = "sqlite+aiosqlite:///./accessible_learning.db"

    # --- Yandex Cloud ---
    YANDEX_API_KEY: str = ""
    YANDEX_FOLDER_ID: str = ""
    YANDEX_GPT_MODEL: str = "yandexgpt-lite"
    YANDEX_GPT_API_URL: str = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

    # --- SpeechKit ---
    SPEECHKIT_API_URL: str = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
    SPEECHKIT_RECOGNITION_API_URL: str = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"

    # --- Vision (OCR) ---
    VISION_API_URL: str = "https://vision.api.cloud.yandex.net/vision/v1/batchAnalyze"

    # --- Qdrant (векторная БД) ---
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION_NAME: str = "knowledge_base"
    QDRANT_API_KEY: str = ""

    # --- Алиса (навык) ---
    ALICE_SKILL_ID: str = ""
    ALICE_OAUTH_TOKEN: str = ""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    """Возвращает кэшированный экземпляр настроек."""
    return Settings()

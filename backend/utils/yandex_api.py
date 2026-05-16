"""
Утилиты для вызова Yandex Cloud API (GPT, SpeechKit, Vision).
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import httpx

from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ──────────────────────────── YandexGPT ───────────────────────────────


async def call_yandex_gpt(
    messages: list[dict[str, str]],
    *,
    system_prompt: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 2000,
) -> str:
    """Вызов YandexGPT API для генерации текста.

    Args:
        messages: Список сообщений в формате [{"role": "user", "text": "..."}].
        system_prompt: Системный промпт для задания поведения модели.
        temperature: Температура генерации (0–1).
        max_tokens: Максимальное количество токенов в ответе.

    Returns:
        Сгенерированный текст.
    """
    if not settings.YANDEX_API_KEY:
        raise RuntimeError("YANDEX_API_KEY не задан. Вызов YandexGPT невозможен.")

    if not settings.YANDEX_FOLDER_ID:
        raise RuntimeError("YANDEX_FOLDER_ID не задан. Вызов YandexGPT невозможен.")

    # Формируем payload согласно документации YandexGPT
    prompt_messages = []
    if system_prompt:
        prompt_messages.append({"role": "system", "text": system_prompt})
    prompt_messages.extend(messages)

    payload = {
        "modelUri": f"gpt://{settings.YANDEX_FOLDER_ID}/{settings.YANDEX_GPT_MODEL}",
        "completionOptions": {
            "stream": False,
            "temperature": temperature,
            "maxTokens": str(max_tokens),
        },
        "messages": prompt_messages,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {settings.YANDEX_API_KEY}",
        "x-folder-id": settings.YANDEX_FOLDER_ID,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            settings.YANDEX_GPT_API_URL,
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()
        return data["result"]["alternatives"][0]["message"]["text"]




# ──────────────────────────── SpeechKit (TTS) ─────────────────────────


async def synthesize_speech(text: str, *, voice: str = "alena", speed: float = 1.0) -> bytes:
    """Синтез речи через Yandex SpeechKit.

    Args:
        text: Текст для озвучивания.
        voice: Имя голоса (alena, filipp, etc.).
        speed: Скорость озвучивания.

    Returns:
        Аудиоданные в формате OGG/Opus.
    """
    if not settings.YANDEX_API_KEY:
        raise RuntimeError("YANDEX_API_KEY не задан. Синтез речи невозможен.")

    headers = {
        "Authorization": f"Api-Key {settings.YANDEX_API_KEY}",
    }
    data = {
        "text": text,
        "voice": voice,
        "speed": str(speed),
        "folderId": settings.YANDEX_FOLDER_ID,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            settings.SPEECHKIT_API_URL,
            headers=headers,
            data=data,
        )
        response.raise_for_status()
        return response.content


# ──────────────────────────── Vision (OCR) ────────────────────────────


async def recognize_text_from_image(image_bytes: bytes) -> str:
    """Распознавание текста на изображении через Yandex Vision.

    Args:
        image_bytes: Байты изображения.

    Returns:
        Распознанный текст.
    """
    if not settings.YANDEX_API_KEY:
        raise RuntimeError("YANDEX_API_KEY не задан. Распознавание изображений невозможно.")

    import base64

    encoded_image = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "folderId": settings.YANDEX_FOLDER_ID,
        "analyze_specs": [
            {
                "content": encoded_image,
                "features": [
                    {"type": "TEXT_DETECTION", "textDetectionConfig": {"languageCodes": ["ru", "en"]}}
                ],
            }
        ],
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {settings.YANDEX_API_KEY}",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            settings.VISION_API_URL,
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

    # Извлекаем текст из результата
    try:
        text_blocks = data["results"][0]["results"][0]["textDetection"]["pages"][0]["blocks"]
        return " ".join(block["lines"][0]["text"] for block in text_blocks)
    except (KeyError, IndexError):
        logger.warning("Не удалось извлечь текст из ответа Vision API")
        return ""

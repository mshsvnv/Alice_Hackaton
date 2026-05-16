"""
Маршруты для голосового интерфейса на фронтенде.

Проксирует запросы к Yandex SpeechKit API:
- TTS (синтез речи) — озвучивание текста
- ASR (распознавание речи) — распознавание голосового ввода
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import Response

from backend.utils.yandex_api import synthesize_speech

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["Голосовой интерфейс"])


# ──────────────────────────── TTS (Синтез речи) ──────────────────────


@router.post(
    "/tts",
    summary="Синтез речи (TTS)",
    response_class=Response,
    responses={
        200: {
            "content": {"audio/ogg": {"schema": {"type": "string", "format": "binary"}}},
            "description": "Аудиоданные в формате OGG/Opus",
        }
    },
)
async def text_to_speech(
    text: str = Form(..., description="Текст для озвучивания"),
    voice: str = Form("alena", description="Голос: alena, filipp, omazh, etc."),
    speed: float = Form(1.0, description="Скорость озвучивания (0.1–3.0)"),
) -> Response:
    """Синтезирует речь из текста через Yandex SpeechKit.

    Возвращает аудиоданные в формате OGG/Opus, которые можно
    воспроизвести в браузере через HTML5 Audio API.
    """
    try:
        audio_data = await synthesize_speech(text, voice=voice, speed=speed)
        return Response(
            content=audio_data,
            media_type="audio/ogg",
            headers={
                "Cache-Control": "no-cache",
                "Content-Disposition": "inline; filename=speech.ogg",
            },
        )
    except RuntimeError as e:
        logger.error(f"Ошибка TTS: {e}")
        return Response(
            content=f'{{"error": "{e}"}}',
            status_code=503,
            media_type="application/json",
        )
    except Exception as e:
        logger.error(f"Неожиданная ошибка TTS: {e}")
        return Response(
            content='{"error": "Внутренняя ошибка сервера"}',
            status_code=500,
            media_type="application/json",
        )


# ──────────────────────────── ASR (Распознавание речи) ──────────────


@router.post(
    "/asr",
    summary="Распознавание речи (ASR)",
    response_model=dict,
)
async def speech_to_text(
    audio: UploadFile = File(..., description="Аудиофайл в формате OGG/Opus или WAV/PCM"),
    language: str = Form("ru-RU", description="Код языка (ru-RU, en-US, etc.)"),
) -> dict[str, str | list[str]]:
    """Распознаёт речь из аудиофайла через Yandex SpeechKit.

    Принимает аудиоданные, записанные в браузере через MediaRecorder API,
    и возвращает распознанный текст.
    """
    import httpx

    from backend.config import get_settings

    settings = get_settings()

    if not settings.YANDEX_API_KEY:
        return {"error": "YANDEX_API_KEY не задан. Распознавание речи невозможно."}

    try:
        audio_bytes = await audio.read()

        headers = {
            "Authorization": f"Api-Key {settings.YANDEX_API_KEY}",
        }

        params = {
            "lang": language,
            "folderId": settings.YANDEX_FOLDER_ID,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                settings.SPEECHKIT_RECOGNITION_API_URL,
                headers=headers,
                params=params,
                content=audio_bytes,
            )
            response.raise_for_status()
            data = response.json()

        # Извлекаем распознанный текст
        result = data.get("result", "")
        if isinstance(result, str):
            return {"text": result}
        elif isinstance(result, list):
            # Если вернулся список альтернатив
            texts = [item.get("text", "") for item in result if isinstance(item, dict)]
            return {"text": texts[0] if texts else "", "alternatives": texts}
        else:
            return {"text": str(result)}

    except httpx.HTTPStatusError as e:
        logger.error(f"Ошибка ASR API: {e.response.status_code} {e.response.text}")
        return {"error": f"Ошибка сервиса распознавания речи: {e.response.status_code}"}
    except Exception as e:
        logger.error(f"Неожиданная ошибка ASR: {e}")
        return {"error": "Внутренняя ошибка сервера при распознавании речи"}


# ──────────────────────────── Проверка доступности ──────────────────


@router.get(
    "/status",
    summary="Статус голосового интерфейса",
)
async def voice_status() -> dict[str, str | bool]:
    """Проверяет доступность голосового интерфейса (TTS и ASR)."""
    from backend.config import get_settings

    settings = get_settings()

    tts_available = bool(settings.YANDEX_API_KEY and settings.YANDEX_FOLDER_ID)
    asr_available = bool(settings.YANDEX_API_KEY and settings.YANDEX_FOLDER_ID)

    return {
        "tts_available": tts_available,
        "asr_available": asr_available,
        "voice": "alena",
        "language": "ru-RU",
    }

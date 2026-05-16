"""
Конфигурация pytest для тестов «Алиса. Доступное Обучение».
"""

import asyncio
from typing import Generator

import pytest


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Создаёт event loop для асинхронных тестов."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

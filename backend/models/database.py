"""
Модели базы данных SQLAlchemy для «Алиса. Доступное Обучение».
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Базовый класс для всех моделей."""

    pass


class UserModel(Base):
    """Модель пользователя (профиля)."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    disability_type: Mapped[str] = mapped_column(String(50), default="none")
    interaction_mode: Mapped[str] = mapped_column(String(20), default="both")
    preferences: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TestModel(Base):
    """Модель теста — публичный, доступен по ссылке."""

    __tablename__ = "tests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    author_id: Mapped[str] = mapped_column(String(36), nullable=False)
    disability_type: Mapped[str] = mapped_column(String(50), default="none")
    content: Mapped[str] = mapped_column(Text, nullable=False)  # JSON-строка с вопросами
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    share_link: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class TestResultModel(Base):
    """Модель результата прохождения теста."""

    __tablename__ = "test_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    test_id: Mapped[str] = mapped_column(String(36), nullable=False)
    answers: Mapped[str] = mapped_column(Text, nullable=False)  # JSON-строка
    score: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class DocumentModel(Base):
    """Модель загруженного документа."""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="uploaded")  # uploaded, processed, error
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

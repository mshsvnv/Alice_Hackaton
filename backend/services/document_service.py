"""
Сервис обработки документов (OCR, парсинг).
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Optional

from backend.utils.yandex_api import call_yandex_gpt, recognize_text_from_image

logger = logging.getLogger(__name__)

# Временное in-memory хранилище для прототипа
_documents_db: dict[str, dict[str, Any]] = {}


class DocumentService:
    """Сервис для загрузки и обработки документов."""

    @staticmethod
    async def upload_document(filename: str, file_content: bytes) -> dict[str, Any]:
        """Загружает и обрабатывает документ.

        Args:
            filename: Имя файла.
            file_content: Содержимое файла в байтах.

        Returns:
            Информация о загруженном документе.
        """
        doc_id = str(uuid.uuid4())

        # Определяем тип файла и извлекаем текст
        extracted_text = ""
        if filename.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
            # Используем OCR для изображений
            extracted_text = await recognize_text_from_image(file_content)
        elif filename.lower().endswith(".txt"):
            # Читаем текстовый файл напрямую
            try:
                extracted_text = file_content.decode("utf-8")
            except UnicodeDecodeError:
                extracted_text = file_content.decode("cp1251", errors="replace")
        elif filename.lower().endswith(".json"):
            try:
                data = json.loads(file_content.decode("utf-8"))
                extracted_text = json.dumps(data, ensure_ascii=False, indent=2)
            except json.JSONDecodeError:
                extracted_text = ""
        else:
            # Для PDF/DOCX — заглушка (требуются дополнительные библиотеки)
            extracted_text = f"[Содержимое файла {filename} — требуется обработка]"

        doc_data = {
            "id": doc_id,
            "filename": filename,
            "extracted_text": extracted_text,
            "status": "processed" if extracted_text else "error",
        }
        _documents_db[doc_id] = doc_data

        logger.info(f"Загружен документ: {doc_id} ({filename}), статус: {doc_data['status']}")
        return doc_data

    @staticmethod
    async def get_document(doc_id: str) -> Optional[dict[str, Any]]:
        """Возвращает информацию о документе по идентификатору."""
        return _documents_db.get(doc_id)

    @staticmethod
    async def list_documents() -> list[dict[str, Any]]:
        """Возвращает список всех документов."""
        return list(_documents_db.values())

    @staticmethod
    async def parse_test_from_text(text: str) -> dict[str, Any]:
        """Парсит структуру теста из текста.

        Поддерживаемые форматы:
        1. Вопрос: <текст> / Вопрос N: <текст>
        2. N. <текст> / N) <текст> (нумерованные вопросы)
        3. А) / А. / A) / A. — варианты ответов (русские и английские буквы)
        4. Ответ: Б / Ответ: B — указание правильного ответа

        Args:
            text: Текст с вопросами теста.

        Returns:
            Структурированный тест.
        """
        import re

        questions = []
        current_question: dict[str, Any] = {}
        option_index = 0
        # Поддержка русских и английских букв
        correct_map = {
            "а": 0, "б": 1, "в": 2, "г": 3,
            "a": 0, "b": 1, "c": 2, "d": 3,
        }

        for line in text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue

            # Паттерн 1: "Вопрос:" или "Вопрос N:"
            if re.match(r"^вопрос\s*\d*\s*:", line.lower()):
                if current_question and current_question.get("text"):
                    questions.append(current_question)
                question_text = re.sub(r"^вопрос\s*\d*\s*:\s*", "", line, flags=re.IGNORECASE)
                current_question = {
                    "id": str(uuid.uuid4()),
                    "text": question_text.strip(),
                    "options": [],
                    "correct_option_index": 0,
                }
                option_index = 0

            # Паттерн 2: Нумерованные вопросы "1." "1)" "1."
            elif re.match(r"^\d+[\.\)]\s*\S", line):
                if current_question and current_question.get("text"):
                    questions.append(current_question)
                question_text = re.sub(r"^\d+[\.\)]\s*", "", line).strip()
                current_question = {
                    "id": str(uuid.uuid4()),
                    "text": question_text,
                    "options": [],
                    "correct_option_index": 0,
                }
                option_index = 0

            # Паттерн 3: Варианты ответа (А), Б), A), B) и т.д.
            elif re.match(r"^[абвгabcd]\s*[\)\.]", line.lower()):
                option_text = re.sub(r"^[абвгabcd]\s*[\)\.]\s*", "", line, flags=re.IGNORECASE).strip()
                if current_question:
                    current_question["options"].append(option_text)
                    option_index += 1

            # Паттерн 4: "Ответ: Б" или "Ответ: B"
            elif line.lower().startswith("ответ:"):
                answer = line.split(":", 1)[-1].strip().lower()
                if current_question and answer in correct_map:
                    current_question["correct_option_index"] = correct_map[answer]

        # Добавляем последний вопрос
        if current_question and current_question.get("text"):
            questions.append(current_question)

        test_id = str(uuid.uuid4())
        return {
            "id": test_id,
            "title": "Извлечённый тест",
            "questions": questions,
        }

    @staticmethod
    async def generate_questions(
        text: str, *, complexity: str = "same", count: int = 5,
    ) -> dict[str, Any]:
        """Генерирует вопросы из текста конспекта с помощью YandexGPT.

        Args:
            text: Текст конспекта.
            complexity: Сложность — "same" (не менять), "simple" (упростить) или "advanced" (усложнить).
            count: Количество вопросов (1–10).

        Returns:
            Словарь со списком сгенерированных вопросов.
        """
        complexity_map = {
            "same": "обычной (не менять уровень сложности)",
            "simple": "упрощённой",
            "advanced": "усложнённой",
        }
        complexity_label = complexity_map.get(complexity, complexity_map["same"])
        system_prompt = (
            "Ты — опытный преподаватель, создающий тесты для проверки знаний по предмету. "
            "Ты должен сгенерировать вопросы строго в формате JSON. "
            "Ответ должен содержать ТОЛЬКО JSON, без пояснений и без markdown-обёрток."
        )
        user_prompt = (
            f"Ниже приведён конспект по определённой теме. "
            f"Сгенерируй {count} вопросов {complexity_label} сложности строго по содержанию данного конспекта. "
            f"Каждый вопрос должен проверять знание конкретных фактов, определений, концепций и идей, "
            f"изложенных в тексте. Вопросы должны быть привязаны к конкретному материалу конспекта — "
            f"нельзя задавать общие вопросы, ответ на которые можно дать без чтения текста. "
            f"Используй точные формулировки и термины из конспекта.\n\n"
            f"Конспект:\n{text}\n\n"
            f"Формат ответа — строго JSON:\n"
            f'{{"questions": [{{"text": "Текст вопроса", '
            f'"options": ["Вариант А", "Вариант Б", "Вариант В", "Вариант Г"], '
            f'"correct": 0}}]}}\n'
            f"Где correct — индекс правильного ответа (0–3). "
            f"Ответь ТОЛЬКО JSON, без markdown-обёрток."
        )

        try:
            raw = await call_yandex_gpt(
                messages=[{"role": "user", "text": user_prompt}],
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=3000,
            )
        except Exception as exc:
            logger.error(f"Ошибка вызова YandexGPT для генерации вопросов: {exc}")
            raise RuntimeError(f"Ошибка генерации вопросов: {exc}") from exc

        # Парсим JSON из ответа
        questions = DocumentService._parse_gpt_questions(raw)
        return {"questions": questions}

    @staticmethod
    def _parse_gpt_questions(raw_text: str) -> list[dict[str, Any]]:
        """Разбирает JSON-ответ YandexGPT в список вопросов."""
        import re

        # Убираем возможные markdown-обёртки ```json ... ```
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            # Попробуем найти JSON-объект в тексте
            match = re.search(r"\{[\s\S]*\}", cleaned)
            if match:
                try:
                    data = json.loads(match.group())
                except json.JSONDecodeError:
                    logger.error(f"Не удалось распарсить JSON из ответа GPT (даже после извлечения): {raw_text[:300]}")
                    return []
            else:
                logger.error(f"Не удалось найти JSON в ответе GPT: {raw_text[:200]}")
                return []

        raw_questions = data.get("questions", [])
        result = []
        for q in raw_questions:
            options = q.get("options", [])
            if not isinstance(options, list) or len(options) < 2:
                continue
            correct = q.get("correct", 0)
            if not isinstance(correct, int) or correct < 0 or correct >= len(options):
                correct = 0
            result.append({
                "id": str(uuid.uuid4()),
                "text": q.get("text", ""),
                "options": options,
                "correct_option_index": correct,
            })
        return result

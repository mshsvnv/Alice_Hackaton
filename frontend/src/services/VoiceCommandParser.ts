/**
 * Парсер голосовых команд для тестового интерфейса.
 *
 * Распознаёт команды из распознанного текста:
 * - Ответы: цифры 1-4 (с или без слова «номер»/«вариант»/«ответ»),
 *   буквенные А-Г, словесные первый-четвёртый, один-четыре
 * - Подсказка: "подсказка", "помоги", "объясни"
 * - Навигация: "повтори", "ещё раз", "назад"
 * - Завершение: "завершить", "стоп", "закончить"
 * - Пауза: "пауза", "перерыв"
 * - Продолжение: "продолжить", "дальше"
 *
 * Приоритет: специфические команды (подсказка, повтор и т.д.)
 * проверяются раньше распознавания цифр, чтобы «подсказка 1»
 * не интерпретировалась как ответ.
 */

export type VoiceCommandType =
  | 'answer'
  | 'hint'
  | 'repeat'
  | 'next'
  | 'prev'
  | 'finish'
  | 'pause'
  | 'resume'
  | 'start'
  | 'unknown';

export interface VoiceCommand {
  type: VoiceCommandType;
  /** Индекс выбранного варианта (0-3) для типа 'answer' */
  answerIndex?: number;
  /** Буква ответа для типа 'answer' */
  answerLetter?: string;
  /** Оригинальный распознанный текст */
  rawText: string;
}

/**
 * Разбирает распознанный текст и возвращает команду.
 */
export function parseVoiceCommand(text: string): VoiceCommand {
  const normalized = text.trim().toLowerCase();
  // Убираем пунктуацию для более надёжного распознавания
  const cleaned = normalized.replace(/[.,!?;:]/g, '').trim();

  // ─── Сначала проверяем специфические команды (приоритет над цифрами) ───

  // ─── Подсказка ───
  if (anyMatch(cleaned, ['подсказк', 'помог', 'объясни', 'не понимаю', 'подскажи'])) {
    return { type: 'hint', rawText: text };
  }

  // ─── Повтор ───
  if (anyMatch(cleaned, ['повтори', 'ещё раз', 'еще раз', 'повтор', 'скажи ещё', 'скажи еще'])) {
    return { type: 'repeat', rawText: text };
  }

  // ─── Следующий вопрос ───
  if (anyMatch(cleaned, ['дальше', 'следующий', 'вперёд', 'вперед', 'продолжить'])) {
    return { type: 'next', rawText: text };
  }

  // ─── Предыдущий вопрос ───
  if (anyMatch(cleaned, ['назад', 'предыдущий', 'предыдущ'])) {
    return { type: 'prev', rawText: text };
  }

  // ─── Завершение теста ───
  if (anyMatch(cleaned, ['заверш', 'стоп', 'законч', 'конец', 'всё', 'все', 'хватит'])) {
    return { type: 'finish', rawText: text };
  }

  // ─── Пауза ───
  if (anyMatch(cleaned, ['пауз', 'перерыв', 'приостанов', 'остановк'])) {
    return { type: 'pause', rawText: text };
  }

  // ─── Продолжение после паузы ───
  if (anyMatch(cleaned, ['продолж', 'возобнов', 'готов'])) {
    return { type: 'resume', rawText: text };
  }

  // ─── Начало ───
  if (anyMatch(cleaned, ['начать', 'начни', 'старт', 'поехали', 'давай'])) {
    return { type: 'start', rawText: text };
  }

  // ─── Ответ: цифры 1, 2, 3, 4 ───
  const digitMap: Record<string, number> = {
    '1': 0,
    '2': 1,
    '3': 2,
    '4': 3,
  };

  // Проверяем прямое совпадение с цифрой (без пунктуации)
  if (cleaned in digitMap) {
    return {
      type: 'answer',
      answerIndex: digitMap[cleaned],
      answerLetter: cleaned,
      rawText: text,
    };
  }

  // Проверяем, содержит ли текст цифру 1-4 (с или без ключевого слова)
  for (const digit of Object.keys(digitMap)) {
    if (cleaned.includes(digit)) {
      return {
        type: 'answer',
        answerIndex: digitMap[digit],
        answerLetter: digit,
        rawText: text,
      };
    }
  }

  // ─── Ответ: первый, второй, третий, четвёртый ───
  const numberMap: Record<string, number> = {
    'первый': 0,
    'второй': 1,
    'третий': 2,
    'четвёртый': 3,
    'четвертый': 3,
    'один': 0,
    'два': 1,
    'три': 2,
    'четыре': 3,
  };

  for (const [word, index] of Object.entries(numberMap)) {
    if (cleaned.includes(word)) {
      return {
        type: 'answer',
        answerIndex: index,
        answerLetter: String(index + 1),
        rawText: text,
      };
    }
  }

  // ─── Неизвестная команда ───
  return { type: 'unknown', rawText: text };
}

/**
 * Проверяет, содержит ли текст любое из ключевых слов.
 */
function anyMatch(text: string, keywords: string[]): boolean {
  return keywords.some((keyword) => text.includes(keyword));
}

/**
 * Формирует текст для озвучивания вопроса с вариантами ответов.
 * Включает audio_description, если оно есть (для слабовидящих).
 */
export function formatQuestionForSpeech(
  questionText: string,
  options: string[],
  questionNumber: number,
  totalQuestions: number,
  audioDescription?: string | null,
): string {
  const optionsText = options
    .map((opt, idx) => `${idx + 1}) ${opt}`)
    .join('. ');

  let text = `Вопрос ${questionNumber} из ${totalQuestions}. ${questionText}.`;

  // Добавляем аудио-описание для слабовидящих
  if (audioDescription) {
    text += ` Пояснение: ${audioDescription}.`;
  }

  text += ` Варианты ответов: ${optionsText}. Назовите номер ответа: 1, 2, 3 или 4.`;

  return text;
}

/**
 * Формирует текст приветствия для голосового помощника.
 */
export function formatWelcomeSpeech(): string {
  return (
    'Добро пожаловать в тест. Я — ваш голосовой помощник. ' +
    'Краткие правила управления. ' +
    'Чтобы ответить, назовите номер варианта: 1, 2, 3 или 4. ' +
    'Для подсказки скажите "подсказка". ' +
    'Чтобы повторить вопрос, скажите "повтори". ' +
    'Чтобы перейти к следующему вопросу, скажите "дальше". ' +
    'Чтобы вернуться, скажите "назад". ' +
    'Для завершения теста скажите "завершить". ' +
    'Начинаем тест.'
  );
}

/**
 * Формирует текст подтверждения ответа.
 */
export function formatAnswerConfirmation(num: string): string {
  return `Вы выбрали вариант ${num}. Записано.`;
}

/**
 * Формирует текст результата теста.
 */
export function formatResultSpeech(correct: number, total: number, percentage: number): string {
  const emoji = percentage >= 80 ? 'Отлично!' : percentage >= 50 ? 'Хорошо!' : 'Нужно подтянуть знания.';
  return (
    `Тест завершён. ${emoji} ` +
    `Вы правильно ответили на ${correct} из ${total} вопросов. ` +
    `Ваш результат: ${percentage} процентов. ` +
    `Спасибо за прохождение теста!`
  );
}

/**
 * Формирует текст подсказки.
 */
export function formatHintSpeech(hintText: string, questionText: string, options: string[]): string {
  const optionsText = options
    .map((opt, idx) => `${idx + 1}) ${opt}`)
    .join('. ');

  return (
    `Вот подсказка: ${hintText}. ` +
    `Повторяю вопрос: ${questionText}. ` +
    `Варианты ответов: ${optionsText}. ` +
    `Назовите номер ответа.`
  );
}

/**
 * Формирует текст ошибки распознавания.
 */
export function formatUnrecognizedSpeech(): string {
  return (
    'Извините, я не поняла вашу команду. ' +
    'Назовите номер ответа: 1, 2, 3 или 4. ' +
    'Для подсказки скажите "подсказка". ' +
    'Чтобы повторить вопрос, скажите "повтори".'
  );
}

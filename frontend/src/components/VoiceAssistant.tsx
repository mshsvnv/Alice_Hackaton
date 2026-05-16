/**
 * Компонент голосового помощника для слабовидящих пользователей.
 *
 * FAB-кнопка (правый нижний угол) — единственный переключатель голоса.
 * Для тестов со слабовидением кнопка включена по умолчанию.
 *
 * Логика:
 * 1. При активации — озвучивает приветствие с правилами, затем первый вопрос
 * 2. При смене вопроса — озвучивает новый вопрос
 * 3. После озвучивания — переходит в режим прослушивания
 * 4. При получении финального результата распознавания — обрабатывает команду
 * 5. При завершении теста — озвучивает результат
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { SpeechService } from '../services/SpeechService';
import {
  parseVoiceCommand,
  formatQuestionForSpeech,
  formatWelcomeSpeech,
  formatAnswerConfirmation,
  formatResultSpeech,
  formatHintSpeech,
  formatUnrecognizedSpeech,
  type VoiceCommand,
} from '../services/VoiceCommandParser';
import type { TestQuestion } from '../api/types';

export interface VoiceAssistantProps {
  /** Тип ОВЗ теста — для автоматического включения */
  disabilityType: string;
  /** Текущий вопрос */
  currentQuestion: TestQuestion | null;
  /** Номер текущего вопроса (начиная с 0) */
  currentQuestionIndex: number;
  /** Общее количество вопросов */
  totalQuestions: number;
  /** Выбранный ответ на текущий вопрос */
  currentAnswer: number | undefined;
  /** Тест завершён */
  finished: boolean;
  /** Количество правильных ответов */
  correctCount: number;
  /** Результат в процентах */
  scorePercentage: number;
  /** Обработчик выбора ответа */
  onSelectAnswer: (optionIndex: number) => void;
  /** Обработчик перехода к следующему вопросу */
  onNext: () => void;
  /** Обработчик перехода к предыдущему вопросу */
  onPrev: () => void;
  /** Обработчик завершения теста */
  onFinish: () => void;
  /** Обработчик запроса подсказки */
  onHint: () => Promise<string | null>;
  /** Текст подсказки (если есть) */
  hintText: string | null;
}

type VoiceState = 'idle' | 'speaking' | 'listening' | 'processing' | 'confirming-finish';

export const VoiceAssistant: React.FC<VoiceAssistantProps> = ({
  disabilityType,
  currentQuestion,
  currentQuestionIndex,
  totalQuestions,
  currentAnswer,
  finished,
  correctCount,
  scorePercentage,
  onSelectAnswer,
  onNext,
  onPrev,
  onFinish,
  onHint,
  hintText,
}) => {
  const [voiceState, setVoiceState] = useState<VoiceState>('idle');
  const [isActive, setIsActive] = useState(true);
  const [lastTranscript, setLastTranscript] = useState('');
  const [error, setError] = useState<string | null>(null);

  // Рефы для предотвращения дублирования
  const isSpeakingRef = useRef(false);
  const isActiveRef = useRef(true);
  const commandProcessedRef = useRef(false);
  const lastSpokenQuestionIdx = useRef<number>(-1);
  const hasWelcomed = useRef(false);
  const hasSpokenResult = useRef(false);
  const lastSpokenHintRef = useRef<string | null>(null);
  const awaitingFinishConfirm = useRef(false);
  const listeningTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Рефы для актуальных обработчиков (избегаем устаревших замыканий)
  const handleCommandRef = useRef<(cmd: VoiceCommand) => void>(() => {});
  const handleActivateRef = useRef<() => void>(() => {});

  // Синхронизируем реф с состоянием
  useEffect(() => {
    isActiveRef.current = isActive;
  }, [isActive]);

  // ─── Автозапуск помощника (для всех тестов) ───
  useEffect(() => {
    // Небольшая задержка, чтобы тест успел загрузиться
    // Используем реф, чтобы при повторном маунте (StrictMode) вызвать актуальный handleActivate
    const timer = setTimeout(() => {
      handleActivateRef.current();
    }, 500);
    return () => clearTimeout(timer);
  }, []);

  // ─── Озвучивание нового вопроса при смене ───
  useEffect(() => {
    if (!isActive || !currentQuestion || finished) return;
    // Не озвучиваем вопрос до завершения приветствия —
    // handleActivate сам вызовет speakQuestion после инструкций
    if (!hasWelcomed.current) return;

    // Озвучиваем только если вопрос действительно изменился
    if (lastSpokenQuestionIdx.current !== currentQuestionIndex) {
      lastSpokenQuestionIdx.current = currentQuestionIndex;
      speakQuestion(currentQuestion, currentQuestionIndex, totalQuestions);
    }
  }, [isActive, currentQuestion, currentQuestionIndex, totalQuestions, finished]);

  // ─── Озвучивание результата при завершении ───
  useEffect(() => {
    if (!isActive || !finished) return;

    if (!hasSpokenResult.current) {
      hasSpokenResult.current = true;
      SpeechService.stopListening();
      speakResult(correctCount, totalQuestions, scorePercentage);
    }
  }, [isActive, finished, correctCount, totalQuestions, scorePercentage]);

  // ─── Активация голосового помощника ───
  const handleActivate = useCallback(async () => {
    // Защита от повторного запуска (StrictMode / двойной клик)
    if (hasWelcomed.current || isSpeakingRef.current) return;

    setIsActive(true);
    lastSpokenQuestionIdx.current = -1;
    hasSpokenResult.current = false;
    lastSpokenHintRef.current = null;
    hasWelcomed.current = false;

    // Озвучиваем приветствие с правилами
    try {
      isSpeakingRef.current = true;
      setVoiceState('speaking');
      const text = formatWelcomeSpeech();
      await SpeechService.speak(text);
      isSpeakingRef.current = false;
      hasWelcomed.current = true;

      // Если уже есть вопрос — озвучиваем его
      if (currentQuestion && !finished) {
        lastSpokenQuestionIdx.current = currentQuestionIndex;
        speakQuestion(currentQuestion, currentQuestionIndex, totalQuestions);
      } else {
        startListening();
      }
    } catch (err) {
      console.error('Ошибка активации голосового помощника:', err);
      setError('Ошибка активации');
      isSpeakingRef.current = false;
      setVoiceState('idle');
    }
  }, [currentQuestion, currentQuestionIndex, totalQuestions, finished]);

  // ─── Деактивация ───
  const handleDeactivate = useCallback(() => {
    SpeechService.cancel();
    isSpeakingRef.current = false;
    hasWelcomed.current = false;
    setIsActive(false);
    setVoiceState('idle');
    setLastTranscript('');
    setError(null);
  }, []);

  // ─── Переключатель (FAB-кнопка) ───
  const handleToggle = useCallback(() => {
    if (isActive) {
      handleDeactivate();
    } else {
      handleActivate();
    }
  }, [isActive, handleActivate, handleDeactivate]);

  // ─── Озвучивание вопроса ───
  const speakQuestion = useCallback(
    async (question: TestQuestion, index: number, total: number) => {
      // Предотвращаем дублирование
      if (isSpeakingRef.current) {
        SpeechService.stopSpeaking();
        // Небольшая пауза для очистки
        await new Promise((r) => setTimeout(r, 100));
      }

      try {
        isSpeakingRef.current = true;
        setVoiceState('speaking');
        const text = formatQuestionForSpeech(
          question.text,
          question.options,
          index + 1,
          total,
          question.audio_description,
        );
        await SpeechService.speak(text);
        isSpeakingRef.current = false;

        // После озвучивания вопроса начинаем слушать ответ
        if (isActiveRef.current) {
          startListening();
        }
      } catch (err) {
        console.error('Ошибка озвучивания вопроса:', err);
        setError('Ошибка озвучивания');
        isSpeakingRef.current = false;
        setVoiceState('idle');
      }
    },
    [],
  );

  // ─── Озвучивание результата ───
  const speakResult = useCallback(
    async (correct: number, total: number, percentage: number) => {
      try {
        isSpeakingRef.current = true;
        setVoiceState('speaking');
        const text = formatResultSpeech(correct, total, percentage);
        await SpeechService.speak(text);
        isSpeakingRef.current = false;
        setVoiceState('idle');
      } catch (err) {
        console.error('Ошибка озвучивания результата:', err);
        isSpeakingRef.current = false;
        setVoiceState('idle');
      }
    },
    [],
  );

  // ─── Озвучивание подсказки ───
  const speakHint = useCallback(
    async (hint: string, question: TestQuestion) => {
      try {
        isSpeakingRef.current = true;
        setVoiceState('speaking');
        const text = formatHintSpeech(hint, question.text, question.options);
        await SpeechService.speak(text);
        isSpeakingRef.current = false;

        if (isActiveRef.current) {
          startListening();
        }
      } catch (err) {
        console.error('Ошибка озвучивания подсказки:', err);
        isSpeakingRef.current = false;
        setVoiceState('idle');
      }
    },
    [],
  );

  // ─── Очистка таймаута прослушивания ───
  const clearListeningTimeout = useCallback(() => {
    if (listeningTimeoutRef.current) {
      clearTimeout(listeningTimeoutRef.current);
      listeningTimeoutRef.current = null;
    }
  }, []);

  // ─── Таймаут прослушивания — если нет ответа, просим повторить ───
  const LISTENING_TIMEOUT_MS = 10_000; // 10 секунд

  // Реф для разрыва циклической зависимости между startListening и handleListeningTimeout
  const startListeningRef = useRef<() => void>(() => {});

  const handleListeningTimeout = useCallback(async () => {
    if (commandProcessedRef.current) return; // Уже обработали команду
    commandProcessedRef.current = true;

    console.log('[VoiceAssistant] Таймаут прослушивания — перезапуск');
    SpeechService.stopListening();

    try {
      isSpeakingRef.current = true;
      setVoiceState('speaking');
      await SpeechService.speak('Я вас не услышала. Пожалуйста, повторите ответ.');
      isSpeakingRef.current = false;
    } catch {
      isSpeakingRef.current = false;
    }

    if (isActiveRef.current) {
      startListeningRef.current();
    }
  }, []);

  // ─── Начало прослушивания ───
  const startListening = useCallback(() => {
    setVoiceState('listening');
    setError(null);
    commandProcessedRef.current = false;

    // Очищаем предыдущий таймаут
    clearListeningTimeout();

    // Запускаем таймаут — если нет ответа, просим повторить
    listeningTimeoutRef.current = setTimeout(() => {
      handleListeningTimeout();
    }, LISTENING_TIMEOUT_MS);

    SpeechService.startListening(
      (text: string, isFinal: boolean) => {
        setLastTranscript(text);

        // Обрабатываем только финальные результаты
        if (isFinal && !commandProcessedRef.current) {
          commandProcessedRef.current = true;
          clearListeningTimeout();
          setVoiceState('processing');
          const command = parseVoiceCommand(text);
          // Используем реф, чтобы всегда вызывать актуальный обработчик
          handleCommandRef.current(command);
        }
      },
      (err: Error) => {
        console.error('Ошибка распознавания:', err);
        setError(err.message);
      },
    );
  }, [clearListeningTimeout, handleListeningTimeout]);

  // ─── Обработка голосовой команды ───
  const handleCommand = useCallback(
    async (command: VoiceCommand) => {
      // Останавливаем прослушивание на время обработки
      SpeechService.stopListening();

      // ─── Обработка подтверждения завершения теста ───
      if (awaitingFinishConfirm.current) {
        awaitingFinishConfirm.current = false;
        const normalized = command.rawText.trim().toLowerCase();
        if (normalized.includes('да') || command.type === 'start') {
          // Пользователь подтвердил — завершаем тест
          try {
            isSpeakingRef.current = true;
            setVoiceState('speaking');
            await SpeechService.speak('Тест завершается.');
            isSpeakingRef.current = false;
          } catch {
            isSpeakingRef.current = false;
          }
          onFinish();
        } else {
          // Пользователь отменил — продолжаем
          try {
            isSpeakingRef.current = true;
            setVoiceState('speaking');
            await SpeechService.speak('Хорошо, продолжаем тест.');
            isSpeakingRef.current = false;
          } catch {
            isSpeakingRef.current = false;
          }
          if (isActiveRef.current) {
            startListening();
          }
        }
        return;
      }

      switch (command.type) {
        case 'answer': {
          if (command.answerIndex !== undefined) {
            onSelectAnswer(command.answerIndex);

            try {
              isSpeakingRef.current = true;
              setVoiceState('speaking');
              const text = formatAnswerConfirmation(command.answerLetter || '');
              await SpeechService.speak(text);
              isSpeakingRef.current = false;

              // Если это последний вопрос — спрашиваем о завершении
              if (currentQuestionIndex >= totalQuestions - 1) {
                awaitingFinishConfirm.current = true;
                setVoiceState('confirming-finish');
                await SpeechService.speak(
                  'Вы ответили на последний вопрос. Завершить тест? ' +
                  'Скажите "да" для завершения или "нет" для продолжения.'
                );
                isSpeakingRef.current = false;
                if (isActiveRef.current) {
                  startListening();
                }
              } else {
                // Переходим к следующему вопросу
                onNext();
              }
            } catch {
              isSpeakingRef.current = false;
              setVoiceState('idle');
            }
          }
          break;
        }

        case 'hint': {
          try {
            isSpeakingRef.current = true;
            setVoiceState('speaking');
            const hint = await onHint();
            if (hint && currentQuestion) {
              const text = formatHintSpeech(hint, currentQuestion.text, currentQuestion.options);
              await SpeechService.speak(text);
            } else {
              await SpeechService.speak('Подсказка недоступна для этого вопроса.');
            }
            isSpeakingRef.current = false;
            if (isActiveRef.current) {
              startListening();
            }
          } catch {
            isSpeakingRef.current = false;
            setVoiceState('idle');
          }
          break;
        }

        case 'repeat': {
          if (currentQuestion) {
            speakQuestion(currentQuestion, currentQuestionIndex, totalQuestions);
          }
          break;
        }

        case 'next': {
          onNext();
          break;
        }

        case 'prev': {
          onPrev();
          break;
        }

        case 'finish': {
          // Спрашиваем подтверждение перед завершением
          try {
            isSpeakingRef.current = true;
            setVoiceState('confirming-finish');
            awaitingFinishConfirm.current = true;
            await SpeechService.speak(
              'Вы уверены, что хотите завершить тест? ' +
              'Скажите "да" для подтверждения или "нет" для продолжения.'
            );
            isSpeakingRef.current = false;
            if (isActiveRef.current) {
              startListening();
            }
          } catch {
            isSpeakingRef.current = false;
            setVoiceState('idle');
          }
          break;
        }

        case 'start': {
          if (currentQuestion) {
            speakQuestion(currentQuestion, currentQuestionIndex, totalQuestions);
          }
          break;
        }

        default: {
          try {
            isSpeakingRef.current = true;
            setVoiceState('speaking');
            const text = formatUnrecognizedSpeech();
            await SpeechService.speak(text);
            isSpeakingRef.current = false;
            if (isActiveRef.current) {
              startListening();
            }
          } catch {
            isSpeakingRef.current = false;
            setVoiceState('idle');
          }
          break;
        }
      }
    },
    [currentQuestion, currentQuestionIndex, totalQuestions, onSelectAnswer, onNext, onPrev, onFinish, onHint, speakQuestion, startListening],
  );

  // Синхронизируем реф обработчика команд с актуальной версией
  // Это решает проблему устаревших замыканий в startListening
  useEffect(() => {
    handleCommandRef.current = handleCommand;
  }, [handleCommand]);

  // Синхронизируем реф startListening с актуальной версией
  useEffect(() => {
    startListeningRef.current = startListening;
  }, [startListening]);

  // Синхронизируем реф handleActivate с актуальной версией
  useEffect(() => {
    handleActivateRef.current = handleActivate;
  }, [handleActivate]);

  // ─── Очистка при размонтировании ───
  useEffect(() => {
    return () => {
      if (listeningTimeoutRef.current) {
        clearTimeout(listeningTimeoutRef.current);
      }
      SpeechService.cancel();
    };
  }, []);

  return (
    <div className="voice-assistant">
      {/* Индикатор состояния (всегда видимый) */}
      {isActive && (
        <div className={`voice-assistant__status voice-assistant__status--${voiceState}`}>
          <div className="voice-assistant__indicator">
            {voiceState === 'speaking' && (
              <div className="voice-assistant__waves">
                <span className="voice-assistant__wave" />
                <span className="voice-assistant__wave" />
                <span className="voice-assistant__wave" />
                <span className="voice-assistant__wave" />
                <span className="voice-assistant__wave" />
              </div>
            )}
            {voiceState === 'listening' && (
              <div className="voice-assistant__pulse" />
            )}
            {voiceState === 'processing' && (
              <div className="voice-assistant__spinner" />
            )}
          </div>

          <span className="voice-assistant__label">
            {voiceState === 'speaking' && 'Озвучиваю...'}
            {voiceState === 'listening' && 'Слушаю...'}
            {voiceState === 'processing' && 'Обрабатываю...'}
            {voiceState === 'confirming-finish' && 'Подтверждение...'}
            {voiceState === 'idle' && 'Готов'}
          </span>

          {/* Последний распознанный текст */}
          {lastTranscript && (
            <span className="voice-assistant__transcript">
              «{lastTranscript}»
            </span>
          )}

          {/* Ошибка */}
          {error && (
            <span className="voice-assistant__error">
              {error}
            </span>
          )}
        </div>
      )}
    </div>
  );
};

/**
 * Страница прохождения теста.
 * - Голосовой помощник автоматически запускается для тестов со слабовидением и ОДА.
 * - Для когнитивных особенностей: упрощённый интерфейс, без голосового помощника.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { testApi } from '../api/client';
import { DISABILITY_LABELS, type TestResponse, type TestQuestion } from '../api/types';
import { VoiceAssistant } from '../components/VoiceAssistant';

export const TestRunPage: React.FC = () => {
  const { testId } = useParams<{ testId: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [test, setTest] = useState<TestResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Состояние прохождения
  const [currentIdx, setCurrentIdx] = useState(0);
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [finished, setFinished] = useState(false);
  const [score, setScore] = useState(0);
  const [correctCount, setCorrectCount] = useState(0);
  const [saving, setSaving] = useState(false);

  // Подсказка
  const [hintText, setHintText] = useState<string | null>(null);

  useEffect(() => {
    loadTest();
  }, [testId]);

  const loadTest = async () => {
    if (!testId) return;
    setLoading(true);
    try {
      const t = await testApi.get(testId);
      setTest(t);
    } catch (err: any) {
      setError(err.message || 'Тест не найден');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectOption = (questionIdx: number, optionIdx: number) => {
    setAnswers((prev) => ({ ...prev, [questionIdx]: optionIdx }));
    setHintText(null);
  };

  const handleNext = () => {
    if (!test) return;
    setHintText(null);
    if (currentIdx < test.questions.length - 1) {
      setCurrentIdx((prev) => prev + 1);
    }
  };

  const handlePrev = () => {
    setHintText(null);
    if (currentIdx > 0) {
      setCurrentIdx((prev) => prev - 1);
    }
  };

  const handleFinish = async () => {
    if (!test || !user) return;

    let correct = 0;
    test.questions.forEach((q, idx) => {
      if (answers[idx] === q.correct_option_index) {
        correct++;
      }
    });
    const finalScore = Math.round((correct / test.questions.length) * 100);
    setScore(finalScore);
    setCorrectCount(correct);
    setFinished(true);

    setSaving(true);
    try {
      await testApi.saveResult({
        user_profile_id: user.id,
        test_id: test.id,
        answers: Object.entries(answers).map(([qIdx, optIdx]) => ({
          question_index: parseInt(qIdx),
          selected_option: optIdx,
        })),
        score: finalScore,
      });
    } catch {
      // ignore save error
    } finally {
      setSaving(false);
    }
  };

  // Обработчик запроса подсказки
  const handleVoiceHint = useCallback(async (): Promise<string | null> => {
    if (!test || !user) return null;

    const question = test.questions[currentIdx];
    if (!question) return null;

    try {
      const res = await fetch('/api/v1/knowledge/hint', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_query: question.text,
          user_profile_id: user.id,
          current_question_text: question.text,
        }),
      });

      if (!res.ok) return null;

      const data = await res.json();
      const hint = data.hint_text || null;
      setHintText(hint);
      return hint;
    } catch {
      return null;
    }
  }, [test, currentIdx, user]);

  if (loading) {
    return <div className="loading-spinner">Загрузка теста...</div>;
  }

  if (error || !test) {
    return (
      <div>
        <div className="alert alert--error">{error || 'Тест не найден'}</div>
        <button className="btn btn--secondary" onClick={() => navigate('/')}>На главную</button>
      </div>
    );
  }

  // ─── Результат ───
  const isCognitive = test.disability_type === 'cognitive';

  if (finished) {
    const correctAnswersCount = Object.entries(answers).filter(([qIdx, optIdx]) => test.questions[parseInt(qIdx)]?.correct_option_index === optIdx).length;
    return (
      <div className={`test-result ${isCognitive ? 'test-result--cognitive' : ''}`}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>
          {score >= 80 ? '🎉' : score >= 50 ? '👍' : '📚'}
        </div>
        <div className="test-result__score">{score}%</div>
        <div className="test-result__label">
          Правильных ответов: {correctAnswersCount} из {test.questions.length}
        </div>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'center' }}>
          <button className="btn btn--primary btn--lg" onClick={() => navigate('/')}>
            На главную
          </button>
          <button className="btn btn--secondary btn--lg" onClick={() => {
            setFinished(false);
            setCurrentIdx(0);
            setAnswers({});
            setHintText(null);
          }}>
            Пройти снова
          </button>
        </div>

        {/* Голосовой помощник на странице результата — только для слабовидения и ОДА */}
        {!isCognitive && (
          <VoiceAssistant
            disabilityType={test.disability_type}
            currentQuestion={null}
            currentQuestionIndex={0}
            totalQuestions={test.questions.length}
            currentAnswer={undefined}
            finished={finished}
            correctCount={correctCount}
            scorePercentage={score}
            onSelectAnswer={() => {}}
            onNext={() => {}}
            onPrev={() => {}}
            onFinish={() => {}}
            onHint={async () => null}
            hintText={null}
          />
        )}
      </div>
    );
  }

  // ─── Прохождение теста ───
  const question: TestQuestion = test.questions[currentIdx];
  const progress = ((currentIdx + 1) / test.questions.length) * 100;
  const allAnswered = test.questions.length === Object.keys(answers).length;
  const currentAnswer = answers[currentIdx];

  return (
    <div className={`test-run ${isCognitive ? 'test-run--cognitive' : ''}`}>
      <div className="test-run__header">
        <h2 className="test-run__title">{test.title}</h2>
        {test.disability_type !== 'none' && (
          <span className="badge badge--primary" style={{ marginBottom: 8 }}>
            {DISABILITY_LABELS[test.disability_type]}
          </span>
        )}
        <div className="test-run__progress">
          Вопрос {currentIdx + 1} из {test.questions.length}
        </div>
        <div className="test-run__progress-bar">
          <div className="test-run__progress-fill" style={{ width: `${progress}%` }} />
        </div>
      </div>

      <div className={`question-card ${isCognitive ? 'question-card--cognitive' : ''}`}>
        <div className="question-card__number">Вопрос {currentIdx + 1}</div>
        <div className="question-card__text">{question.text}</div>

        {question.image_description && (
          <div className="question-card__image-desc">
            🖼️ {question.image_description}
          </div>
        )}

        <div className="flex flex-col gap-2">
          {question.options.map((option, optIdx) => {
            const num = optIdx + 1;
            const isSelected = currentAnswer === optIdx;
            // Цветовая кодировка для когнитивного режима
            const colorClass = isCognitive
              ? `option-btn--cognitive-${optIdx}`
              : '';
            return (
              <button
                key={optIdx}
                className={`option-btn ${isSelected ? 'option-btn--selected' : ''} ${colorClass}`}
                onClick={() => handleSelectOption(currentIdx, optIdx)}
                aria-label={`Вариант ${num}: ${option}`}
              >
                <span className="option-btn__letter">{num}</span>
                <span>{option}</span>
              </button>
            );
          })}
        </div>

        {/* Подсказка */}
        {hintText && (
          <div className="hint-card" role="alert">
            <div className="hint-card__icon">💡</div>
            <div className="hint-card__text">{hintText}</div>
          </div>
        )}
      </div>

      <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
        {currentIdx > 0 && (
          <button className="btn btn--secondary btn--lg" style={{ flex: 1 }} onClick={handlePrev}>
            ← Назад
          </button>
        )}

        {!hintText && (
          <button
            className="btn btn--secondary btn--lg"
            style={{ flex: 1 }}
            onClick={handleVoiceHint}
            title="Получить подсказку"
          >
            💡 Подсказка
          </button>
        )}

        {currentIdx < test.questions.length - 1 ? (
          <button
            className="btn btn--primary btn--lg"
            style={{ flex: 2 }}
            onClick={handleNext}
            disabled={currentAnswer === undefined}
          >
            Далее →
          </button>
        ) : (
          <button
            className="btn btn--primary btn--lg"
            style={{ flex: 2 }}
            onClick={handleFinish}
            disabled={!allAnswered || saving}
          >
            {saving ? 'Сохранение...' : 'Завершить тест'}
          </button>
        )}
      </div>

      {/* Голосовой помощник — только для слабовидения и ОДА, НЕ для когнитивных */}
      {!isCognitive && (
        <VoiceAssistant
          disabilityType={test.disability_type}
          currentQuestion={question}
          currentQuestionIndex={currentIdx}
          totalQuestions={test.questions.length}
          currentAnswer={currentAnswer}
          finished={finished}
          correctCount={correctCount}
          scorePercentage={score}
          onSelectAnswer={(optIdx) => handleSelectOption(currentIdx, optIdx)}
          onNext={handleNext}
          onPrev={handlePrev}
          onFinish={handleFinish}
          onHint={handleVoiceHint}
          hintText={hintText}
        />
      )}
    </div>
  );
};

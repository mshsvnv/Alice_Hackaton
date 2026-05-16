/**
 * Страница создания теста — пошаговый интерфейс.
 *
 * Шаги:
 * 1. Ввод названия и текста теста (или загрузка файла) + динамическое превью
 * 2. Выбор типа адаптации и создание теста
 * 3. Превью итогового теста с ссылкой
 */

import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { testApi, documentApi } from '../api/client';
import {
  DISABILITY_LABELS,
  type DisabilityType,
  type TestQuestion,
  type TestResponse,
} from '../api/types';

type CreationStep = 'input' | 'adapt' | 'result';

export const CreateTestPage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Текущий шаг
  const [step, setStep] = useState<CreationStep>('input');

  // Шаг 1: Ввод данных
  const [title, setTitle] = useState('');
  const [testText, setTestText] = useState('');
  const [inputMode, setInputMode] = useState<'file' | 'text' | 'generate'>('file');
  const [uploading, setUploading] = useState(false);
  const [uploadedDocId, setUploadedDocId] = useState('');
  const [parsedQuestions, setParsedQuestions] = useState<TestQuestion[]>([]);
  const [parseError, setParseError] = useState('');
  const [parsing, setParsing] = useState(false);

  // Генерация вопросов из конспекта
  const [genComplexity, setGenComplexity] = useState<'same' | 'simple' | 'advanced'>('same');
  const [genCount, setGenCount] = useState(5);
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState('');

  // Шаг 2: Адаптация
  const [disabilityType, setDisabilityType] = useState<DisabilityType>('none');
  const [creating, setCreating] = useState(false);

  // Шаг 3: Результат
  const [createdTest, setCreatedTest] = useState<TestResponse | null>(null);

  // Общие
  const [error, setError] = useState('');

  // ─── Динамический парсинг текста ───

  const parseTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const parseTestText = useCallback(async (text: string) => {
    if (!text.trim()) {
      setParsedQuestions([]);
      setParseError('');
      return;
    }

    setParsing(true);
    setParseError('');
    try {
      const result = await documentApi.parseTest(text);
      const questions = result.questions as TestQuestion[] | undefined;
      if (questions && Array.isArray(questions) && questions.length > 0) {
        setParsedQuestions(questions);
      } else {
        setParsedQuestions([]);
        setParseError('Не удалось распознать вопросы в тексте');
      }
    } catch (err: any) {
      setParsedQuestions([]);
      setParseError(err.message || 'Ошибка парсинга');
    } finally {
      setParsing(false);
    }
  }, []);

  // Debounced парсинг при изменении текста
  useEffect(() => {
    if (inputMode !== 'text') return;

    if (parseTimerRef.current) {
      clearTimeout(parseTimerRef.current);
    }

    parseTimerRef.current = setTimeout(() => {
      parseTestText(testText);
    }, 800);

    return () => {
      if (parseTimerRef.current) {
        clearTimeout(parseTimerRef.current);
      }
    };
  }, [testText, inputMode, parseTestText]);

  // ─── Загрузка файла ───

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setError('');
    setParsedQuestions([]);
    try {
      const doc = await documentApi.upload(file);
      setUploadedDocId(doc.id);

      // Если есть извлечённый текст — парсим его для превью
      if (doc.extracted_text) {
        setTestText(doc.extracted_text);
        parseTestText(doc.extracted_text);
      }
    } catch (err: any) {
      setError(err.message || 'Ошибка загрузки файла');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // ─── Загрузка файла для генерации ───

  const genFileInputRef = useRef<HTMLInputElement>(null);
  const [genFileText, setGenFileText] = useState('');
  const [genUploading, setGenUploading] = useState(false);

  const handleGenFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setGenUploading(true);
    setGenError('');
    try {
      const doc = await documentApi.upload(file);
      if (doc.extracted_text) {
        setGenFileText(doc.extracted_text);
        // Автогенерация вопросов с настройками по умолчанию
        setGenerating(true);
        setGenError('');
        try {
          const result = await documentApi.generateQuestions(doc.extracted_text, genComplexity, genCount);
          const questions = result.questions as TestQuestion[] | undefined;
          if (questions && Array.isArray(questions) && questions.length > 0) {
            setParsedQuestions(questions);
            setParseError('');
          } else {
            setGenError('Не удалось сгенерировать вопросы');
          }
        } catch (genErr: any) {
          setGenError(genErr.message || 'Ошибка генерации вопросов');
        } finally {
          setGenerating(false);
        }
      } else {
        setGenError('Не удалось извлечь текст из файла');
      }
    } catch (err: any) {
      setGenError(err.message || 'Ошибка загрузки файла');
    } finally {
      setGenUploading(false);
      if (genFileInputRef.current) genFileInputRef.current.value = '';
    }
  };

  // ─── Генерация вопросов из конспекта ───

  const handleGenerate = async () => {
    const sourceText = inputMode === 'generate' ? genFileText : testText;
    if (!sourceText.trim() || sourceText.trim().length < 10) return;

    setGenerating(true);
    setGenError('');
    try {
      const result = await documentApi.generateQuestions(sourceText, genComplexity, genCount);
      const questions = result.questions as TestQuestion[] | undefined;
      if (questions && Array.isArray(questions) && questions.length > 0) {
        setParsedQuestions(questions);
        setParseError('');
      } else {
        setGenError('Не удалось сгенерировать вопросы');
      }
    } catch (err: any) {
      setGenError(err.message || 'Ошибка генерации вопросов');
    } finally {
      setGenerating(false);
    }
  };

  // ─── Переходы между шагами ───

  const canGoToAdapt = () => {
    if (!title.trim()) return false;
    if (inputMode === 'file') return !!uploadedDocId;
    return parsedQuestions.length > 0;
  };

  const handleGoToAdapt = () => {
    if (!canGoToAdapt()) return;
    setError('');
    setStep('adapt');
  };

  const handleCreate = async () => {
    if (!user?.id) return;

    setCreating(true);
    setError('');
    try {
      let result: TestResponse;
      if (inputMode === 'file' && uploadedDocId) {
        result = await testApi.createFromDocument(
          uploadedDocId, title, user.id, disabilityType
        );
      } else if (parsedQuestions.length > 0) {
        result = await testApi.create({
          title,
          author_id: user.id,
          disability_type: disabilityType,
          questions: parsedQuestions,
          is_public: true,
        });
      } else {
        return;
      }
      setCreatedTest(result);
      setStep('result');
    } catch (err: any) {
      setError(err.message || 'Ошибка создания теста');
    } finally {
      setCreating(false);
    }
  };

  const [copied, setCopied] = useState(false);

  const handleCopyLink = () => {
    if (!createdTest?.share_link) return;
    const url = `${window.location.origin}/share/${createdTest.share_link}`;
    navigator.clipboard.writeText(url).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  // ─── Рендер ───

  // Шаг 3: Результат
  if (step === 'result' && createdTest) {
    return (
      <div>
        <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 20 }}>Создать тест</h1>

        {/* Индикатор шагов */}
        <div className="steps-indicator">
          <div className="steps-indicator__track" />
          <div className="steps-indicator__progress steps-indicator__progress--step-3" />
          <div className="step-item step-item--done">
            <div className="step-item__circle">✓</div>
            <div className="step-item__label">Текст</div>
          </div>
          <div className="step-item step-item--done">
            <div className="step-item__circle">✓</div>
            <div className="step-item__label">Адаптация</div>
          </div>
          <div className="step-item step-item--active">
            <div className="step-item__circle">3</div>
            <div className="step-item__label">Готово</div>
          </div>
        </div>

        <div className="card" style={{ marginTop: 16 }}>
          <div className="card__header">
            <span className="card__title">✅ Тест создан!</span>
          </div>

          <div style={{ marginBottom: 16 }}>
            <p style={{ fontSize: 16, fontWeight: 600, marginBottom: 4 }}>{createdTest.title}</p>
            <p style={{ fontSize: 14, color: 'var(--color-text-secondary)' }}>
              {createdTest.questions.length} вопросов
              {createdTest.disability_type !== 'none' && (
                <span className="badge badge--primary" style={{ marginLeft: 8 }}>
                  {DISABILITY_LABELS[createdTest.disability_type]}
                </span>
              )}
            </p>
          </div>

          {/* Превью вопросов */}
          <div className="test-preview">
            {createdTest.questions.map((q, idx) => (
              <div key={q.id} className="test-preview__question">
                <div className="test-preview__question-text">
                  <strong>{idx + 1}.</strong> {q.text}
                </div>
                <div className="test-preview__options">
                  {q.options.map((opt, optIdx) => (
                    <div
                      key={optIdx}
                      className={`test-preview__option ${optIdx === q.correct_option_index ? 'test-preview__option--correct' : ''}`}
                    >
                      {String.fromCharCode(1040 + optIdx)}) {opt}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {createdTest.share_link && (
            <div className="form-group" style={{ marginTop: 16 }}>
              <label className="form-label">Ссылка для прохождения</label>
              <div className="share-link-box">
                <span className="share-link-box__text">
                  {window.location.origin}/share/{createdTest.share_link}
                </span>
                <button className="btn btn--sm btn--primary" onClick={handleCopyLink}>
                  {copied ? '✅ Скопировано' : '📋 Копировать'}
                </button>
              </div>
            </div>
          )}

          <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
            <button
              className="btn btn--primary btn--lg"
              style={{ flex: 1 }}
              onClick={() => navigate(`/test/${createdTest.id}`)}
            >
              Пройти тест
            </button>
            <button
              className="btn btn--secondary btn--lg"
              style={{ flex: 1 }}
              onClick={() => navigate('/')}
            >
              На главную
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 20 }}>Создать тест</h1>

      {/* Индикатор шагов */}
      <div className="steps-indicator">
        <div className="steps-indicator__track" />
        <div className={`steps-indicator__progress steps-indicator__progress--step-${step === 'input' ? '1' : step === 'adapt' ? '2' : '3'}`} />
        <div className={`step-item ${step === 'input' ? 'step-item--active' : 'step-item--done'}`}>
          <div className="step-item__circle">{step === 'input' ? '1' : '✓'}</div>
          <div className="step-item__label">Текст</div>
        </div>
        <div className={`step-item ${step === 'adapt' ? 'step-item--active' : step === 'result' ? 'step-item--done' : ''}`}>
          <div className="step-item__circle">{step === 'adapt' ? '2' : step === 'result' ? '✓' : '2'}</div>
          <div className="step-item__label">Адаптация</div>
        </div>
        <div className={`step-item ${step === 'result' ? 'step-item--active' : ''}`}>
          <div className="step-item__circle">3</div>
          <div className="step-item__label">Готово</div>
        </div>
      </div>

      {error && <div className="alert alert--error" style={{ marginTop: 16 }}>{error}</div>}

      {/* ─── Шаг 1: Ввод названия и текста ─── */}
      {step === 'input' && (
        <div className="create-test-layout" style={{ marginTop: 16 }}>
          {/* Левая часть: форма ввода */}
          <div className="create-test-form">
            <div className="card">
              {/* Переключатель режима ввода */}
              <div className="login-tabs" style={{ marginBottom: 16 }}>
                <button
                  className={`login-tabs__btn ${inputMode === 'file' ? 'login-tabs__btn--active' : ''}`}
                  onClick={() => setInputMode('file')}
                >
                  📁 Загрузить файл
                </button>
                <button
                  className={`login-tabs__btn ${inputMode === 'text' ? 'login-tabs__btn--active' : ''}`}
                  onClick={() => setInputMode('text')}
                >
                  ✏️ Ввести текст
                </button>
                <button
                  className={`login-tabs__btn ${inputMode === 'generate' ? 'login-tabs__btn--active' : ''}`}
                  onClick={() => setInputMode('generate')}
                >
                  🤖 Генерация из конспекта
                </button>
              </div>

              {/* Название теста */}
              <div className="form-group">
                <label className="form-label" htmlFor="testTitle">Название теста</label>
                <input
                  id="testTitle"
                  className="form-input"
                  type="text"
                  placeholder="Например: Биология — Фотосинтез"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
              </div>

              {/* ─── Режим: Загрузить файл ─── */}
              {inputMode === 'file' && (
                <div className="form-group">
                  <div
                    className={`upload-zone ${uploadedDocId ? 'upload-zone--active' : ''}`}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      className="upload-input"
                      accept=".pdf,.docx,.doc,.txt,.png,.jpg,.jpeg"
                      onChange={handleFileUpload}
                      style={{ display: 'none' }}
                    />
                    {uploading ? (
                      <>
                        <div className="upload-zone__icon">⏳</div>
                        <div className="upload-zone__text">Загрузка...</div>
                      </>
                    ) : uploadedDocId ? (
                      <>
                        <div className="upload-zone__icon">✅</div>
                        <div className="upload-zone__text">Документ загружен (ID: {uploadedDocId.slice(0, 8)}...)</div>
                        <div className="upload-zone__hint">Нажмите, чтобы загрузить другой</div>
                      </>
                    ) : (
                      <>
                        <div className="upload-zone__icon">📁</div>
                        <div className="upload-zone__text">Нажмите или перетащите файл</div>
                        <div className="upload-zone__hint">PDF, DOCX, TXT, изображения</div>
                      </>
                    )}
                  </div>
                </div>
              )}

              {/* ─── Режим: Ввести текст ─── */}
              {inputMode === 'text' && (
                <div className="form-group">
                  <label className="form-label" htmlFor="testText">Текст теста</label>
                  <textarea
                    id="testText"
                    className="form-textarea"
                    rows={12}
                    placeholder={`Введите текст теста в формате:\n\nВопрос: Какой процесс происходит в хлоропластах?\nА) Дыхание\nБ) Фотосинтез\nВ) Брожение\nГ) Гниение\nОтвет: Б\n\nВопрос: ...`}
                    value={testText}
                    onChange={(e) => setTestText(e.target.value)}
                  />
                  {parsing && (
                    <div style={{ fontSize: 13, color: 'var(--color-text-secondary)', marginTop: 4 }}>
                      ⏳ Распознавание вопросов...
                    </div>
                  )}
                  {parseError && !parsing && (
                    <div style={{ fontSize: 13, color: '#e53935', marginTop: 4 }}>
                      {parseError}
                    </div>
                  )}
                </div>
              )}

              {/* ─── Режим: Генерация из конспекта ─── */}
              {inputMode === 'generate' && (
                <div className="form-group">
                  <label className="form-label">Загрузите конспект (PDF, TXT)</label>
                  <div
                    className={`upload-zone ${genFileText ? 'upload-zone--active' : ''}`}
                    onClick={() => genFileInputRef.current?.click()}
                    style={{ marginBottom: 12 }}
                  >
                    <input
                      ref={genFileInputRef}
                      type="file"
                      className="upload-input"
                      accept=".pdf,.docx,.doc,.txt,.png,.jpg,.jpeg"
                      onChange={handleGenFileUpload}
                      style={{ display: 'none' }}
                    />
                    {genUploading ? (
                      <>
                        <div className="upload-zone__icon">⏳</div>
                        <div className="upload-zone__text">Загрузка...</div>
                      </>
                    ) : genFileText ? (
                      <>
                        <div className="upload-zone__icon">✅</div>
                        <div className="upload-zone__text">Конспект загружен</div>
                        <div className="upload-zone__hint">Нажмите, чтобы загрузить другой</div>
                      </>
                    ) : (
                      <>
                        <div className="upload-zone__icon">📄</div>
                        <div className="upload-zone__text">Загрузите конспект для генерации вопросов</div>
                        <div className="upload-zone__hint">PDF, DOCX, TXT, изображения</div>
                      </>
                    )}
                  </div>

                  {/* Или ввести текст конспекта вручную */}
                  {!genFileText && (
                    <>
                      <div style={{ fontSize: 13, color: 'var(--color-text-secondary)', marginBottom: 8, textAlign: 'center' }}>
                        или введите текст конспекта вручную
                      </div>
                      <textarea
                        className="form-textarea"
                        rows={6}
                        placeholder="Вставьте текст конспекта..."
                        value={testText}
                        onChange={(e) => setTestText(e.target.value)}
                      />
                    </>
                  )}

                  {/* Настройки генерации */}
                  <div className="generate-questions" style={{ marginTop: 12, padding: '12px 0', borderTop: '1px solid var(--color-border)' }}>
                    <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, color: 'var(--color-text-secondary)' }}>
                      ⚙️ Настройки генерации
                    </div>
                    <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
                      <select
                        className="form-select"
                        value={genComplexity}
                        onChange={(e) => setGenComplexity(e.target.value as 'same' | 'simple' | 'advanced')}
                        style={{ minWidth: 140 }}
                      >
                        <option value="same">Не менять сложность</option>
                        <option value="simple">Упростить</option>
                        <option value="advanced">Усложнить</option>
                      </select>
                      <label style={{ fontSize: 13, display: 'flex', alignItems: 'center', gap: 4 }}>
                        Кол-во:
                        <input
                          type="number"
                          min={1}
                          max={10}
                          value={genCount}
                          onChange={(e) => setGenCount(Math.max(1, Math.min(10, Number(e.target.value) || 1)))}
                          className="form-input"
                          style={{ width: 60, textAlign: 'center' }}
                        />
                      </label>
                      <button
                        className="btn btn--primary"
                        disabled={generating || (!genFileText && testText.trim().length < 10)}
                        onClick={handleGenerate}
                        style={{ whiteSpace: 'nowrap' }}
                      >
                        {generating ? '⏳ Генерация...' : '✨ Сгенерировать'}
                      </button>
                    </div>
                    {genError && !generating && (
                      <div style={{ fontSize: 13, color: '#e53935', marginTop: 6 }}>
                        {genError}
                      </div>
                    )}
                  </div>
                </div>
              )}

              <button
                className="btn btn--primary btn--lg"
                style={{ width: '100%' }}
                disabled={!canGoToAdapt()}
                onClick={handleGoToAdapt}
              >
                Далее →
              </button>
            </div>
          </div>

          {/* Правая часть: динамическое превью */}
          <div className="create-test-preview">
            <div className="card">
              <div className="card__header">
                <span className="card__title">👁️ Превью теста</span>
              </div>

              {parsedQuestions.length === 0 ? (
                <div className="test-preview__empty">
                  <div className="test-preview__empty-icon">📝</div>
                  <div className="test-preview__empty-text">
                    {inputMode === 'text'
                      ? 'Введите текст теста слева — здесь появится превью распознанных вопросов'
                      : inputMode === 'file'
                        ? 'Загрузите файл — здесь появится превью распознанных вопросов'
                        : 'Загрузите конспект и нажмите «Сгенерировать» — здесь появится превью вопросов'}
                  </div>
                </div>
              ) : (
                <div className="test-preview">
                  {title && (
                    <div className="test-preview__title">{title}</div>
                  )}
                  {parsedQuestions.map((q, idx) => (
                    <div key={q.id} className="test-preview__question">
                      <div className="test-preview__question-text">
                        <strong>{idx + 1}.</strong> {q.text}
                      </div>
                      <div className="test-preview__options">
                        {q.options.map((opt, optIdx) => (
                          <div
                            key={optIdx}
                            className={`test-preview__option ${optIdx === q.correct_option_index ? 'test-preview__option--correct' : ''}`}
                          >
                            {String.fromCharCode(1040 + optIdx)}) {opt}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ─── Шаг 2: Выбор типа адаптации ─── */}
      {step === 'adapt' && (
        <div className="card" style={{ marginTop: 16 }}>
          <div className="card__header">
            <span className="card__title">⚙️ Настройки адаптации</span>
          </div>

          <div style={{ marginBottom: 16 }}>
            <p style={{ fontSize: 14, color: 'var(--color-text-secondary)' }}>
              Тест: <strong>{title}</strong> • {parsedQuestions.length} вопросов
            </p>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="disabilityType">Тип адаптации</label>
            <select
              id="disabilityType"
              className="form-select"
              value={disabilityType}
              onChange={(e) => setDisabilityType(e.target.value as DisabilityType)}
            >
              {Object.entries(DISABILITY_LABELS).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>

          {disabilityType !== 'none' && (
            <div className="adaptation-info">
              <div className="adaptation-info__icon">ℹ️</div>
              <div className="adaptation-info__text">
                {disabilityType === 'vision' && 'Будут добавлены аудио-описания для слабовидящих пользователей.'}
                {disabilityType === 'motor' && 'Будут добавлены аудио-описания и голосовое управление для удобства навигации.'}
                {disabilityType === 'cognitive' && 'Текст вопросов будет упрощён, добавлены аналогии и пошаговые подсказки.'}
              </div>
            </div>
          )}

          <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
            <button
              className="btn btn--secondary btn--lg"
              onClick={() => setStep('input')}
            >
              ← Назад
            </button>
            <button
              className="btn btn--primary btn--lg"
              style={{ flex: 1 }}
              disabled={creating}
              onClick={handleCreate}
            >
              {creating ? 'Создание...' : '🚀 Создать тест'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

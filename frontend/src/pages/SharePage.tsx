/**
 * Страница прохождения теста по ссылке (share link).
 * Стиль: Yandex AI Studio — минимализм, профессионализм, лаконичность.
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { testApi } from '../api/client';
import { DISABILITY_LABELS, type TestResponse } from '../api/types';
import { Icon } from '../components/Icon';

export const SharePage: React.FC = () => {
  const { shareLink } = useParams<{ shareLink: string }>();
  const navigate = useNavigate();

  const [test, setTest] = useState<TestResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadTest();
  }, [shareLink]);

  const loadTest = async () => {
    if (!shareLink) return;
    setLoading(true);
    try {
      const t = await testApi.getByShareLink(shareLink);
      setTest(t);
    } catch (err: any) {
      setError(err.message || 'Тест не найден');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="login-page">
        <div className="login-card" style={{ textAlign: 'center' }}>
          <div className="loading-spinner">Загрузка теста...</div>
        </div>
      </div>
    );
  }

  if (error || !test) {
    return (
      <div className="login-page">
        <div className="login-card" style={{ textAlign: 'center' }}>
          <div style={{ marginBottom: 16 }}>
            <Icon name="search" size="xl" style={{ color: 'var(--color-text-muted)' }} aria-label="Тест не найден" />
          </div>
          <h2 style={{ marginBottom: 8 }}>Тест не найден</h2>
          <p style={{ color: 'var(--color-text-secondary)', marginBottom: 16 }}>
            Возможно, ссылка устарела или тест был удалён
          </p>
          <button className="btn btn--primary" onClick={() => navigate('/')}>
            На главную
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="login-page">
      <div className="login-card" style={{ textAlign: 'center' }}>
        <div className="login-card__logo">
          <Icon name="document" size="lg" style={{ color: '#fff' }} aria-label="Тест" />
        </div>
        <h2 style={{ marginBottom: 8 }}>{test.title}</h2>
        <p style={{ color: 'var(--color-text-secondary)', marginBottom: 4 }}>
          {test.questions.length} вопросов
        </p>
        {test.disability_type !== 'none' && (
          <span className="badge badge--primary" style={{ marginBottom: 16 }}>
            {DISABILITY_LABELS[test.disability_type]}
          </span>
        )}
        <div style={{ marginTop: 16 }}>
          <button
            className="btn btn--primary btn--lg"
            style={{ width: '100%' }}
            onClick={() => navigate(`/test/${test!.id}`)}
          >
            Начать тест
          </button>
        </div>
      </div>
    </div>
  );
};

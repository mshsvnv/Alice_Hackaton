/**
 * Главная страница — список публичных тестов и тестов пользователя.
 * Стиль: Yandex AI Studio — минимализм, профессионализм, лаконичность.
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { testApi } from '../api/client';
import { DISABILITY_LABELS, type TestListItem } from '../api/types';
import { Icon } from '../components/Icon';

export const HomePage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [publicTests, setPublicTests] = useState<TestListItem[]>([]);
  const [myTests, setMyTests] = useState<TestListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'public' | 'my'>('public');

  useEffect(() => {
    loadTests();
  }, [user]);

  const loadTests = async () => {
    setLoading(true);
    try {
      const pub = await testApi.listPublic();
      setPublicTests(pub);
      if (user?.id) {
        const mine = await testApi.listByAuthor(user.id);
        setMyTests(mine);
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  const handleTakeTest = (testId: string) => {
    navigate(`/test/${testId}`);
  };

  const [copiedId, setCopiedId] = useState<string | null>(null);

  const handleCopyLink = (shareLink: string) => {
    const url = `${window.location.origin}/share/${shareLink}`;
    navigator.clipboard.writeText(url).then(() => {
      setCopiedId(shareLink);
      setTimeout(() => setCopiedId(null), 2000);
    });
  };

  const getDisabilityBadge = (type: string) => {
    if (type === 'none') return null;
    return <span className="badge badge--primary">{DISABILITY_LABELS[type as keyof typeof DISABILITY_LABELS] || type}</span>;
  };

  if (loading) {
    return <div className="loading-spinner">Загрузка...</div>;
  }

  const displayedTests = tab === 'public' ? publicTests : myTests;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 style={{ fontSize: 22, fontWeight: 700 }}>Тесты</h1>
        <button className="btn btn--primary" onClick={() => navigate('/create')}>
          <Icon name="add" size="sm" />
          <span>Создать тест</span>
        </button>
      </div>

      <div className="login-tabs" style={{ marginBottom: 20 }}>
        <button
          className={`login-tabs__btn ${tab === 'public' ? 'login-tabs__btn--active' : ''}`}
          onClick={() => setTab('public')}
        >
          Все тесты ({publicTests.length})
        </button>
        <button
          className={`login-tabs__btn ${tab === 'my' ? 'login-tabs__btn--active' : ''}`}
          onClick={() => setTab('my')}
        >
          Мои тесты ({myTests.length})
        </button>
      </div>

      {displayedTests.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state__icon">
            <Icon name="document" size="xl" style={{ color: 'var(--color-text-muted)' }} aria-label="Нет тестов" />
          </div>
          <div className="empty-state__text">
            {tab === 'public' ? 'Пока нет публичных тестов' : 'Вы ещё не создали ни одного теста'}
          </div>
          {tab === 'my' && (
            <button className="btn btn--primary" onClick={() => navigate('/create')}>
              Создать первый тест
            </button>
          )}
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {displayedTests.map((test) => (
            <div key={test.id} className="test-card" onClick={() => handleTakeTest(test.id)}>
              <div className="test-card__icon">
                <Icon name="document" size="md" style={{ color: 'var(--color-primary)' }} aria-hidden />
              </div>
              <div className="test-card__info">
                <div className="test-card__title">{test.title}</div>
                <div className="test-card__meta">
                  <span>{test.questions_count} вопр.</span>
                  {getDisabilityBadge(test.disability_type)}
                </div>
              </div>
              <div className="test-card__actions">
                <button
                  className="btn btn--primary btn--sm"
                  onClick={(e) => { e.stopPropagation(); handleTakeTest(test.id); }}
                >
                  Пройти
                </button>
                {test.share_link && (
                  <button
                    className="btn btn--secondary btn--sm"
                    onClick={(e) => { e.stopPropagation(); handleCopyLink(test.share_link!); }}
                    title="Скопировать ссылку"
                  >
                    {copiedId === test.share_link ? (
                      <><Icon name="check" size="xs" /> Скопировано</>
                    ) : (
                      <Icon name="link" size="xs" aria-label="Скопировать ссылку" />
                    )}
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

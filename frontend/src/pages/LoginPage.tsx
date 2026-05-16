/**
 * Страница входа / регистрации.
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export const LoginPage: React.FC = () => {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [name, setName] = useState('');
  const [profileId, setProfileId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!profileId.trim()) return;
    setLoading(true);
    setError('');
    try {
      await login(profileId.trim());
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Профиль не найден');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setLoading(true);
    setError('');
    try {
      await register(name.trim());
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Ошибка регистрации');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-card__logo">🎓</div>
        <h1 className="login-card__title">Доступное Обучение</h1>
        <p className="login-card__subtitle">Платформа адаптивного тестирования с Алисой</p>

        <div className="login-tabs">
          <button
            className={`login-tabs__btn ${mode === 'login' ? 'login-tabs__btn--active' : ''}`}
            onClick={() => setMode('login')}
          >
            Войти
          </button>
          <button
            className={`login-tabs__btn ${mode === 'register' ? 'login-tabs__btn--active' : ''}`}
            onClick={() => setMode('register')}
          >
            Регистрация
          </button>
        </div>

        {error && <div className="alert alert--error">{error}</div>}

        {mode === 'login' ? (
          <form onSubmit={handleLogin}>
            <div className="form-group">
              <label className="form-label" htmlFor="profileId">ID профиля</label>
              <input
                id="profileId"
                className="form-input"
                type="text"
                placeholder="Вставьте ваш ID профиля"
                value={profileId}
                onChange={(e) => setProfileId(e.target.value)}
                disabled={loading}
              />
            </div>
            <button type="submit" className="btn btn--primary btn--lg" style={{ width: '100%' }} disabled={loading || !profileId.trim()}>
              {loading ? 'Вход...' : 'Войти'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleRegister}>
            <div className="form-group">
              <label className="form-label" htmlFor="name">Ваше имя</label>
              <input
                id="name"
                className="form-input"
                type="text"
                placeholder="Как вас зовут?"
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={loading}
              />
            </div>
            <button type="submit" className="btn btn--primary btn--lg" style={{ width: '100%' }} disabled={loading || !name.trim()}>
              {loading ? 'Регистрация...' : 'Создать профиль'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
};

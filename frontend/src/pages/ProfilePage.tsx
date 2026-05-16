/**
 * Страница профиля пользователя.
 * Стиль: Yandex AI Studio — минимализм, профессионализм, лаконичность.
 */

import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { profileApi } from '../api/client';
import { DISABILITY_LABELS, INTERACTION_LABELS, type DisabilityType, type InteractionMode } from '../api/types';
import { Icon } from '../components/Icon';

export const ProfilePage: React.FC = () => {
  const { user, updateUser } = useAuth();
  const [name, setName] = useState(user?.name || '');
  const [disabilityType, setDisabilityType] = useState<DisabilityType>(user?.disability_type || 'none');
  const [interactionMode, setInteractionMode] = useState<InteractionMode>(user?.interaction_mode || 'both');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user?.id) return;

    setSaving(true);
    setError('');
    setSaved(false);
    try {
      const updated = await profileApi.update(user.id, {
        name,
        disability_type: disabilityType,
        interaction_mode: interactionMode,
      });
      updateUser(updated);
      setSaved(true);
    } catch (err: any) {
      setError(err.message || 'Ошибка сохранения');
    } finally {
      setSaving(false);
    }
  };

  const handleCopyId = () => {
    if (!user?.id) return;
    navigator.clipboard.writeText(user.id).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  if (!user) return null;

  return (
    <div>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 20 }}>Профиль</h1>

      <div className="card">
        <form onSubmit={handleSave}>
          <div className="form-group">
            <label className="form-label" htmlFor="profileName">Имя</label>
            <input
              id="profileName"
              className="form-input"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Ваш ID профиля</label>
            <div className="share-link-box">
              <span className="share-link-box__text">{user.id}</span>
              <button
                type="button"
                className="btn btn--sm btn--primary"
                onClick={handleCopyId}
              >
                {copied ? (
                  <><Icon name="check" size="xs" /> Скопировано</>
                ) : (
                  <Icon name="copy" size="xs" aria-label="Копировать" />
                )}
              </button>
            </div>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="disabilityType">Тип ОВЗ</label>
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

          <div className="form-group">
            <label className="form-label" htmlFor="interactionMode">Способ взаимодействия</label>
            <select
              id="interactionMode"
              className="form-select"
              value={interactionMode}
              onChange={(e) => setInteractionMode(e.target.value as InteractionMode)}
            >
              {Object.entries(INTERACTION_LABELS).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>

          {error && <div className="alert alert--error">{error}</div>}
          {saved && <div className="alert alert--success">Профиль сохранён</div>}

          <button
            type="submit"
            className="btn btn--primary btn--lg"
            style={{ width: '100%' }}
            disabled={saving}
          >
            {saving ? 'Сохранение...' : 'Сохранить'}
          </button>
        </form>
      </div>
    </div>
  );
};

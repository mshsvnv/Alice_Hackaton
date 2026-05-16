/**
 * Основной макет приложения с боковой навигацией.
 * Стиль: Yandex AI Studio — минимализм, профессионализм, лаконичность.
 */

import React, { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import { Icon } from './Icon';

const NAV_ITEMS = [
  { to: '/', label: 'Главная', icon: 'home' as const },
  { to: '/create', label: 'Создать тест', icon: 'add' as const },
  { to: '/profile', label: 'Профиль', icon: 'user' as const },
];

export const Layout: React.FC = () => {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="app-layout">
      {/* Мобильный оверлей */}
      {sidebarOpen && (
        <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Боковая панель */}
      <aside className={`sidebar ${sidebarOpen ? 'sidebar--open' : ''}`}>
        <div className="sidebar__header">
          <span className="sidebar__logo">
            <Icon name="app" size="sm" style={{ color: '#fff' }} aria-label="Алиса" />
          </span>
          <span className="sidebar__title">Алиса</span>
        </div>

        <nav className="sidebar__nav">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `sidebar__link ${isActive ? 'sidebar__link--active' : ''}`
              }
              onClick={() => setSidebarOpen(false)}
              end={item.to === '/'}
            >
              <span className="sidebar__link-icon">
                <Icon name={item.icon} size="sm" />
              </span>
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar__footer">
          <button className="btn btn--ghost" onClick={toggleTheme} style={{ color: 'var(--color-sidebar-text)', width: '100%', justifyContent: 'flex-start' }}>
            <Icon name={theme === 'light' ? 'moon' : 'sun'} size="sm" />
            <span style={{ marginLeft: 6 }}>{theme === 'light' ? 'Тёмная тема' : 'Светлая тема'}</span>
          </button>
          {user && (
            <button className="btn btn--ghost" onClick={handleLogout} style={{ color: 'var(--color-sidebar-text)', width: '100%', justifyContent: 'flex-start' }}>
              <Icon name="logout" size="sm" />
              <span style={{ marginLeft: 6 }}>Выйти</span>
            </button>
          )}
        </div>
      </aside>

      {/* Основной контент */}
      <main className="main-content">
        <header className="top-bar">
          <button
            className="btn btn--icon hamburger"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            aria-label="Меню"
          >
            <Icon name="menu" size="md" />
          </button>
          <h1 className="top-bar__title">Доступное Обучение</h1>
          {user && (
            <span className="top-bar__user">
              {user.name}
            </span>
          )}
        </header>

        <div className="page-content">
          <Outlet />
        </div>
      </main>
    </div>
  );
};

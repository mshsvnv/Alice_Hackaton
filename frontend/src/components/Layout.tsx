/**
 * Основной макет приложения с боковой навигацией.
 */

import React, { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';

const NAV_ITEMS = [
  { to: '/', label: 'Главная', icon: '🏠' },
  { to: '/create', label: 'Создать тест', icon: '➕' },
  { to: '/profile', label: 'Профиль', icon: '👤' },
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
          <span className="sidebar__logo">🎓</span>
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
              <span className="sidebar__link-icon">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar__footer">
          <button className="btn btn--ghost" onClick={toggleTheme} style={{ color: 'var(--color-sidebar-text)', width: '100%', justifyContent: 'flex-start' }}>
            {theme === 'light' ? '🌙 Тёмная тема' : '☀️ Светлая тема'}
          </button>
          {user && (
            <button className="btn btn--ghost" onClick={handleLogout} style={{ color: 'var(--color-sidebar-text)', width: '100%', justifyContent: 'flex-start' }}>
              🚪 Выйти
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
            ☰
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

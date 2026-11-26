import React, { useEffect } from "react";
import { createRoot } from "react-dom/client";
import {
  BrowserRouter,
  Link,
  NavLink,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import { AuthProvider, Protected, useAuth } from "./auth";
import { useAction } from "./hooks";
import { Feedback, PageHead } from "./components/ui";
import Catalog from "./pages/Catalog";
import Project from "./pages/Project";
import Editor from "./pages/Editor";
import Dashboard from "./pages/Dashboard";
import Moderation from "./pages/Moderation";
import { AuthPage, Profile, PublicProfile } from "./pages/Account";
import "./styles.css";

class ErrorBoundary extends React.Component {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? (
      <div className="empty">
        <h1>Не удалось открыть страницу</h1>
        <p>
          Попробуйте обновить её. Если ошибка повторяется, сообщите команде
          проекта.
        </p>
        <button className="button" onClick={() => window.location.reload()}>
          Обновить
        </button>
      </div>
    ) : (
      this.props.children
    );
  }
}
function Rules() {
  return (
    <div className="narrow">
      <PageHead eyebrow="ПРОСТЫЕ ДОГОВОРЁННОСТИ" title="Правила сообщества" />
      <div className="panel prose">
        <h2>Понятные проекты</h2>
        <p>
          Опиши цель, задачи, необходимую помощь и ожидаемую занятость. Не
          обещай то, что не можешь выполнить. Учебные и демонстрационные проекты
          отмечай честно.
        </p>
        <h2>Уважение к людям</h2>
        <p>
          Оскорбления, травля, спам и мошеннические предложения недопустимы.
          Обсуждай условия участия до начала работы. Не передавай чужие контакты
          без согласия.
        </p>
        <h2>Как работает модерация</h2>
        <p>
          Новые и отредактированные проекты проходят проверку. Модератор может
          опубликовать проект или вернуть его с объяснением. На нарушение можно
          пожаловаться со страницы проекта или профиля.
        </p>
        <p>
          Жалоба сама по себе не блокирует публикацию. Модератор проверяет её,
          сохраняет решение и при необходимости скрывает проект или блокирует
          аккаунт. Личность заявителя не показывается автору.
        </p>
        <h2>Контакты команды</h2>
        <p>
          Контакты команды доступны принятым участникам, автору и модераторам.
          После выхода из команды доступ к ним на сайте закрывается.
        </p>
      </div>
    </div>
  );
}
function Shell() {
  const { user, logout, loading } = useAuth();
  const action = useAction();
  const location = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
    document.title = `МАИ.Команда — ${location.pathname === "/" ? "найди свою команду" : "проекты и люди"}`;
  }, [location.pathname]);
  return (
    <>
      <a className="skip-link" href="#main">
        Перейти к содержимому
      </a>
      <header className="site-header">
        <div className="header-inner">
          <Link className="brand" to="/" aria-label="МАИ.Команда — главная">
            <span className="brand-symbol">м↗</span>
            <span>
              МАИ<span className="brand-dot">.</span>Команда
            </span>
          </Link>
          <nav className="main-nav" aria-label="Основная навигация">
            <NavLink to="/" end>
              Проекты
            </NavLink>
            {user && <NavLink to="/dashboard">Мой кабинет</NavLink>}
            {user?.role === "moderator" && (
              <NavLink to="/moderation">Модерация</NavLink>
            )}
          </nav>
          <div className="header-account">
            {loading ? (
              <span className="muted small">Загрузка…</span>
            ) : user ? (
              <>
                <Link className="profile-link" to="/profile">
                  <span className="avatar">{user.name[0]}</span>
                  <span>{user.name.split(" ")[0]}</span>
                </Link>
                <button
                  className="text-button subtle"
                  disabled={action.busy}
                  onClick={() => action.run(logout)}
                >
                  Выйти
                </button>
              </>
            ) : (
              <>
                <Link className="text-button" to="/login">
                  Войти
                </Link>
                <Link className="button small-button" to="/register">
                  Присоединиться ↗
                </Link>
              </>
            )}
          </div>
        </div>
      </header>
      <main id="main" className="container">
        <Feedback {...action} />
        <ErrorBoundary key={location.pathname}>
          <Routes>
            <Route path="/" element={<Catalog />} />
            <Route path="/login" element={<AuthPage key="login" />} />
            <Route
              path="/register"
              element={<AuthPage key="register" register />}
            />
            <Route
              path="/projects/new"
              element={
                <Protected>
                  <Editor />
                </Protected>
              }
            />
            <Route
              path="/projects/:id/edit"
              element={
                <Protected>
                  <Editor />
                </Protected>
              }
            />
            <Route path="/projects/:id" element={<Project />} />
            <Route
              path="/dashboard"
              element={
                <Protected>
                  <Dashboard />
                </Protected>
              }
            />
            <Route
              path="/profile"
              element={
                <Protected>
                  <Profile />
                </Protected>
              }
            />
            <Route
              path="/people/:id"
              element={
                <Protected>
                  <PublicProfile />
                </Protected>
              }
            />
            <Route
              path="/moderation"
              element={
                <Protected moderator>
                  <Moderation />
                </Protected>
              }
            />
            <Route path="/rules" element={<Rules />} />
            <Route
              path="*"
              element={
                <div className="empty">
                  <h1>Такой страницы нет</h1>
                  <Link className="button" to="/">
                    Вернуться к проектам
                  </Link>
                </div>
              }
            />
          </Routes>
        </ErrorBoundary>
      </main>
      <footer className="site-footer">
        <div className="container footer-inner">
          <div>
            <Link className="brand" to="/">
              МАИ<span className="brand-dot">.</span>Команда
            </Link>
            <p>Люди. Идеи. Общее дело.</p>
          </div>
          <p className="small muted">
            Студенческий проект
            <br />
            «Обучение служением»
          </p>
          <Link to="/rules">Правила сообщества ↗</Link>
        </div>
      </footer>
    </>
  );
}
createRoot(document.getElementById("root")).render(
  <BrowserRouter>
    <AuthProvider>
      <Shell />
    </AuthProvider>
  </BrowserRouter>,
);

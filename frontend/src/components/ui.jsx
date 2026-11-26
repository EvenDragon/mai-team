import { Link } from "react-router-dom";
import { useState } from "react";
import { labels, post } from "../api";
import { useAction } from "../hooks";
import { useAuth } from "../auth";
export function Feedback({ error, success }) {
  return (
    <>
      {error && (
        <div className="notice error" role="alert">
          {error}
        </div>
      )}
      {success && (
        <div className="notice success" role="status">
          {success}
        </div>
      )}
    </>
  );
}
export function Resource({ state, children }) {
  if (state.loading)
    return (
      <div className="loading" role="status">
        <span className="spinner" />
        Загружаем…
      </div>
    );
  if (state.error)
    return (
      <div className="empty">
        <Feedback error={state.error} />
        <button className="button secondary" onClick={state.reload}>
          Попробовать снова
        </button>
      </div>
    );
  return children(state.data);
}
export function Empty({ title, children }) {
  return (
    <div className="empty">
      <span className="empty-mark" aria-hidden="true">
        ↗
      </span>
      <h3>{title}</h3>
      {children && <div className="muted">{children}</div>}
    </div>
  );
}
export function Badge({ status }) {
  return (
    <span className={`badge status-${status}`}>{labels[status] || status}</span>
  );
}
export function Skills({ items }) {
  return (
    <div className="tags">
      {items.map((s) => (
        <span className="tag" key={s}>
          {s}
        </span>
      ))}
    </div>
  );
}
export function PageHead({ eyebrow, title, description, children }) {
  return (
    <div className="page-head">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1>{title}</h1>
        {description && <p className="muted">{description}</p>}
      </div>
      {children}
    </div>
  );
}
export function ProjectCard({ project: p, manage = false }) {
  const places = p.vacancies.reduce((n, v) => n + v.capacity - v.filled, 0);
  const categoryIndex = [
    "IT",
    "Инженерия",
    "Наука",
    "Социальные проекты",
    "Дизайн",
  ].indexOf(p.category);
  return (
    <article className="project-card">
      <div className="card-top">
        <span
          className={`category-icon cat-${categoryIndex}`}
          aria-hidden="true"
        >
          {["</>", "◇", "⌁", "↗", "✳"][categoryIndex] || "↗"}
        </span>
        <span className="muted small">
          {p.category} · {p.format}
        </span>
        {p.is_demo && <span className="demo-badge">Демо</span>}
      </div>
      <h3>
        <Link to={`/projects/${p.id}`}>{p.title}</Link>
      </h3>
      <p className="card-description">{p.description}</p>
      <Skills items={p.skills.slice(0, 4)} />
      <div className="card-bottom">
        <span className={p.recruitment_open && places ? "available" : "muted"}>
          <span aria-hidden="true">● </span>
          {p.recruitment_open ? `Свободных мест: ${places}` : "Набор закрыт"}
        </span>
        <Link to={`/projects/${p.id}`} aria-label={`Открыть ${p.title}`}>
          ↗
        </Link>
      </div>
      {manage && (
        <div className="manage-row">
          <Badge status={p.status} />
          <Link to={`/projects/${p.id}/edit`}>Редактировать</Link>
        </div>
      )}
    </article>
  );
}
export function ReportForm({ targetType, targetId }) {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const action = useAction();
  if (!user)
    return (
      <Link className="subtle" to="/login">
        Войдите, чтобы пожаловаться
      </Link>
    );
  if (!open)
    return (
      <button className="text-button subtle" onClick={() => setOpen(true)}>
        Пожаловаться
      </button>
    );
  return (
    <form
      className="report-form"
      onSubmit={(e) => {
        e.preventDefault();
        const f = new FormData(e.currentTarget);
        action.run(
          () =>
            post("/reports", {
              target_type: targetType,
              target_id: Number(targetId),
              reason: f.get("reason"),
              message: f.get("message"),
            }),
          "Жалоба отправлена. Статус доступен в кабинете.",
        );
      }}
    >
      <h3>Сообщить о нарушении</h3>
      <p className="small muted">
        Автор не увидит, кто отправил жалобу. Решение принимает модератор.
      </p>
      <Feedback {...action} />
      {!action.success && (
        <>
          <label>
            Причина
            <select name="reason">
              {["spam", "abuse", "fraud", "other"].map((x) => (
                <option key={x} value={x}>
                  {labels[x]}
                </option>
              ))}
            </select>
          </label>
          <label>
            Что произошло?
            <textarea name="message" maxLength={2000} rows={3} />
          </label>
          <button className="button secondary" disabled={action.busy}>
            Отправить жалобу
          </button>
        </>
      )}
      <button
        type="button"
        className="text-button"
        onClick={() => setOpen(false)}
      >
        Закрыть
      </button>
    </form>
  );
}

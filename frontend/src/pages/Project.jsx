import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, post } from "../api";
import { useAuth } from "../auth";
import { useAction, useResource } from "../hooks";
import {
  Badge,
  Empty,
  Feedback,
  PageHead,
  ReportForm,
  Resource,
  Skills,
} from "../components/ui";

function ApplyForm({ vacancy, onDone }) {
  const [open, setOpen] = useState(false);
  const action = useAction();
  if (!open)
    return (
      <button className="button secondary" onClick={() => setOpen(true)}>
        Хочу в команду ↗
      </button>
    );
  return (
    <form
      className="apply-form"
      onSubmit={(e) => {
        e.preventDefault();
        const message = new FormData(e.currentTarget).get("message");
        action.run(async () => {
          await post(`/vacancies/${vacancy.id}/applications`, { message });
          onDone();
        }, "Отклик отправлен. Решение появится в кабинете.");
      }}
    >
      <Feedback {...action} />
      {!action.success && (
        <>
          <label>
            Почему тебе интересен проект?
            <textarea
              name="message"
              rows={3}
              required
              minLength={10}
              maxLength={2000}
              placeholder="Расскажи, чем можешь помочь. Желание учиться тоже важно."
            />
          </label>
          <div className="actions">
            <button className="button" disabled={action.busy}>
              Отправить отклик
            </button>
            <button
              type="button"
              className="text-button"
              onClick={() => setOpen(false)}
            >
              Отмена
            </button>
          </div>
        </>
      )}
    </form>
  );
}
function Inbox({ id }) {
  const state = useResource(`/projects/${id}/applications`);
  const action = useAction();
  return (
    <section className="panel">
      <h2>Входящие отклики</h2>
      <Feedback {...action} />
      <Resource state={state}>
        {(items) =>
          items.length ? (
            <div className="list">
              {items.map((a) => (
                <article key={a.id} className="list-item">
                  <div className="row spread">
                    <Link to={`/people/${a.user_id}`}>
                      <strong>{a.applicant.name}</strong>
                    </Link>
                    <Badge status={a.status} />
                  </div>
                  <p className="small muted">
                    {a.vacancy_title} ·{" "}
                    {a.applicant.institute || "Группа не указана"}
                  </p>
                  <p className="pre-wrap">{a.message}</p>
                  <Skills items={a.applicant.skills} />
                  {a.status === "pending" && (
                    <div className="actions">
                      {[
                        ["accepted", "Принять"],
                        ["rejected", "Отклонить"],
                      ].map(([status, label]) => (
                        <button
                          key={status}
                          className={`button ${status === "rejected" ? "secondary" : ""}`}
                          disabled={action.busy}
                          onClick={() =>
                            action.run(async () => {
                              await post(`/applications/${a.id}/decision`, {
                                status,
                              });
                              state.reload();
                              window.dispatchEvent(new Event("team-updated"));
                            }, "Решение сохранено")
                          }
                        >
                          {label}
                        </button>
                      ))}
                    </div>
                  )}
                </article>
              ))}
            </div>
          ) : (
            <Empty title="Пока нет откликов">
              Поделись ссылкой на проект с другими студентами.
            </Empty>
          )
        }
      </Resource>
    </section>
  );
}
export default function Project() {
  const { id } = useParams();
  const { user } = useAuth();
  const state = useResource(`/projects/${id}`, user?.id);
  const action = useAction();
  const navigate = useNavigate();
  useEffect(() => {
    window.addEventListener("team-updated", state.reload);
    return () => window.removeEventListener("team-updated", state.reload);
  }, [state.reload]);
  // The inbox is separate to keep its private data out of public project responses.
  return (
    <Resource state={state}>
      {(p) => {
        const owner = user?.id === p.owner_id;
        const member = p.team.some((u) => u.id === user?.id);
        return (
          <>
            <Link className="back-link" to="/">
              ← Все проекты
            </Link>
            <PageHead
              eyebrow={`${p.category} / ${p.format}`}
              title={p.title}
              description={
                p.is_demo ? "Демонстрационный проект — вымышленные данные" : ""
              }
            >
              <Badge status={p.status} />
            </PageHead>
            <Feedback {...action} />
            {p.moderation_note && (
              <div className="notice">
                Комментарий модератора: {p.moderation_note}
              </div>
            )}
            <div className="detail-layout">
              <div className="detail-main">
                <section className="panel">
                  <h2>О проекте</h2>
                  <p className="pre-wrap">{p.description}</p>
                  <Skills items={p.skills} />
                </section>
                <section className="panel">
                  <div className="row spread">
                    <h2>Кого ищем</h2>
                    <span
                      className={p.recruitment_open ? "available" : "muted"}
                    >
                      {p.status !== "published"
                        ? "Набор приостановлен"
                        : p.recruitment_open
                          ? "Набор открыт"
                          : "Набор закрыт"}
                    </span>
                  </div>
                  {p.vacancies.map((v) => (
                    <article className="vacancy" key={v.id}>
                      <div className="row spread">
                        <h3>{v.title}</h3>
                        <span className="tag">
                          {v.filled} / {v.capacity}
                        </span>
                      </div>
                      <p className="pre-wrap">{v.requirements}</p>
                      {!owner &&
                        !member &&
                        p.status === "published" &&
                        p.recruitment_open &&
                        v.filled < v.capacity &&
                        (user ? (
                          <ApplyForm vacancy={v} onDone={() => {}} />
                        ) : (
                          <Link
                            className="button secondary"
                            to="/login"
                            state={{ from: `/projects/${id}` }}
                          >
                            Войти и откликнуться
                          </Link>
                        ))}
                    </article>
                  ))}
                </section>
                {owner && <Inbox id={p.id} />}
              </div>
              <aside className="detail-side">
                <section className="panel">
                  <p className="eyebrow">КОМАНДА ПРОЕКТА</p>
                  <Link className="person" to={`/people/${p.owner_id}`}>
                    <span className="avatar">{p.owner_name[0]}</span>
                    <span>
                      <strong>{p.owner_name}</strong>
                      <small>Автор проекта</small>
                    </span>
                  </Link>
                  {p.team.map((u) => (
                    <div className="member-row" key={u.id}>
                      <Link className="person" to={`/people/${u.id}`}>
                        <span className="avatar soft">{u.name[0]}</span>
                        <span>
                          <strong>{u.name}</strong>
                          <small>{u.vacancy}</small>
                        </span>
                      </Link>
                      {owner && (
                        <button
                          className="text-button danger"
                          disabled={action.busy}
                          onClick={() => {
                            if (window.confirm(`Удалить ${u.name} из команды?`))
                              action.run(async () => {
                                await api(`/projects/${p.id}/members/${u.id}`, {
                                  method: "DELETE",
                                });
                                state.reload();
                              });
                          }}
                        >
                          Удалить
                        </button>
                      )}
                    </div>
                  ))}
                  {!p.team.length && (
                    <p className="muted small">
                      Команда только собирается. Возможно, здесь не хватает
                      тебя.
                    </p>
                  )}
                  {p.team_contact ? (
                    <a
                      className="button full"
                      href={p.team_contact}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Связаться в Telegram ↗
                    </a>
                  ) : (
                    <p className="small muted">
                      {owner || member
                        ? "Автор пока не добавил контакт команды."
                        : "Контакт команды откроется после принятия отклика."}
                    </p>
                  )}
                  {member && (
                    <button
                      className="text-button danger"
                      disabled={action.busy}
                      onClick={() => {
                        if (
                          window.confirm(
                            "Выйти из команды? Доступ к её контакту будет закрыт.",
                          )
                        )
                          action.run(async () => {
                            await api(`/projects/${p.id}/members/${user.id}`, {
                              method: "DELETE",
                            });
                            navigate("/dashboard");
                          });
                      }}
                    >
                      Выйти из команды
                    </button>
                  )}
                </section>
                {owner && (
                  <section className="panel">
                    <h3>Управление</h3>
                    <Link
                      className="button secondary full"
                      to={`/projects/${p.id}/edit`}
                    >
                      Редактировать проект
                    </Link>
                    <button
                      className="button secondary full"
                      disabled={
                        action.busy ||
                        (!p.recruitment_open && p.status !== "published")
                      }
                      onClick={() =>
                        action.run(async () => {
                          await post(`/projects/${p.id}/recruitment`, {
                            open: !p.recruitment_open,
                          });
                          state.reload();
                        })
                      }
                    >
                      {p.recruitment_open ? "Закрыть набор" : "Открыть набор"}
                    </button>
                    <p className="small muted">
                      Закрытый набор сохраняет страницу и доступ команды.
                    </p>
                  </section>
                )}
                {!owner && <ReportForm targetType="project" targetId={p.id} />}
              </aside>
            </div>
          </>
        );
      }}
    </Resource>
  );
}

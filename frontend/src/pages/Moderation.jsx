import { Link, useSearchParams } from "react-router-dom";
import { labels, post } from "../api";
import { useAction, useResource } from "../hooks";
import { Badge, Empty, Feedback, PageHead, Resource, TeamContact } from "../components/ui";

function Review({ item, type, onDone }) {
  const action = useAction();
  return (
    <form
      className="panel review-card"
      onSubmit={(e) => {
        e.preventDefault();
        const f = new FormData(e.currentTarget);
        const decision = f.get("decision");
        const note = f.get("note");
        if (
          (decision === "block" || decision === "hide") &&
          !window.confirm(
            "Применить это ограничение? Причина сохранится в истории.",
          )
        )
          return;
        action.run(async () => {
          await post(
            `/moderation/${type}/${item.id}`,
            type === "projects"
              ? { status: decision, note }
              : { action: decision, note },
          );
          onDone();
        });
      }}
    >
      <div className="row spread">
        <h3>
          <Link
            to={
              type === "projects"
                ? `/projects/${item.id}`
                : item.target_type === "project"
                  ? `/projects/${item.target_id}`
                  : `/people/${item.target_id}`
            }
          >
            {item.title || item.target_name}
          </Link>
        </h3>
        <Badge status={item.status} />
      </div>
      <p className="pre-wrap">{item.description || item.message}</p>
      {type === "reports" && (
        <p className="small muted">Причина: {labels[item.reason]}</p>
      )}
      {item.moderation_note && (
        <div className="notice">Предыдущее решение: {item.moderation_note}</div>
      )}
      {type === "projects" && (
        <>
          <p className="small muted">Автор: {item.owner_name}</p>
          {item.vacancies.map((v) => (
            <p key={v.id}>
              <strong>
                {v.title} ({v.capacity} мест)
              </strong>
              <br />
              {v.requirements}
            </p>
          ))}
          {item.team_contact && <TeamContact value={item.team_contact} />}
        </>
      )}
      <Feedback {...action} />
      <label>
        Решение
        <select name="decision">
          {(type === "projects"
            ? [
                ["published", "Опубликовать"],
                ["rejected", "Вернуть на исправление"],
              ]
            : [
                ["dismiss", "Нарушения нет"],
                ["warn", "Отправить замечание"],
                ...(item.target_type === "project"
                  ? [["hide", "Скрыть проект"]]
                  : []),
                ["block", "Заблокировать аккаунт"],
              ]
          ).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <label>
        Объяснение
        <textarea
          name="note"
          required
          minLength={3}
          maxLength={1000}
          rows={3}
          placeholder="Понятно объясните решение и необходимые действия."
        />
      </label>
      <p className="small muted">
        Не указывайте личность заявителя. Объяснение увидят участники
        рассмотрения.
      </p>
      <button className="button" disabled={action.busy}>
        Сохранить решение
      </button>
    </form>
  );
}
function Queue({ type }) {
  const state = useResource(`/moderation/${type}`);
  const action = useAction();
  return (
    <>
      <Feedback {...action} />
      <Resource state={state}>
        {(items) =>
          !items.length ? (
            <Empty title="Всё разобрано">Новых записей пока нет.</Empty>
          ) : type === "history" ? (
            <div className="panel list">
              {items.map((e) => (
                <article className="list-item" key={e.id}>
                  <strong>{labels[e.action] || e.action}</strong>
                  <p className="pre-wrap">{e.note}</p>
                  <p className="small muted">
                    Модератор #{e.moderator_id} ·{" "}
                    {new Date(e.created_at * 1000).toLocaleString("ru-RU")} ·{" "}
                    {e.project_id
                      ? `Проект #${e.project_id}`
                      : `Пользователь #${e.user_id}`}
                  </p>
                </article>
              ))}
              <p className="muted small">
                Последние 50 решений. Полная история хранится в базе.
              </p>
            </div>
          ) : type === "users" ? (
            <div className="panel list">
              {items.map((u) => (
                <form
                  className="list-item"
                  key={u.id}
                  onSubmit={(e) => {
                    e.preventDefault();
                    const note = new FormData(e.currentTarget).get("note");
                    action.run(async () => {
                      await post(`/moderation/users/${u.id}/block`, {
                        blocked: false,
                        note,
                      });
                      state.reload();
                    });
                  }}
                >
                  <h3>{u.name}</h3>
                  <p>{u.reason}</p>
                  <label>
                    Причина разблокировки
                    <input
                      name="note"
                      minLength={3}
                      maxLength={1000}
                      required
                    />
                  </label>
                  <button className="button secondary" disabled={action.busy}>
                    Разблокировать
                  </button>
                </form>
              ))}
            </div>
          ) : (
            <div className="review-grid">
              {items.map((item) => (
                <Review
                  key={item.id}
                  item={item}
                  type={type}
                  onDone={state.reload}
                />
              ))}
            </div>
          )
        }
      </Resource>
    </>
  );
}
export default function Moderation() {
  const [params, setParams] = useSearchParams();
  const types = [
    ["projects", "Публикации"],
    ["reports", "Жалобы"],
    ["users", "Блокировки"],
    ["history", "История"],
  ];
  const type = types.some(([x]) => x === params.get("tab"))
    ? params.get("tab")
    : "projects";
  return (
    <>
      <PageHead
        eyebrow="ЗАБОТА О СООБЩЕСТВЕ"
        title="Модерация"
        description="Проверяйте понятность задач и соблюдение правил, а не привлекательность идеи."
      />
      <nav className="tabs" aria-label="Разделы модерации">
        {types.map(([x, label]) => (
          <button
            key={x}
            className={type === x ? "active" : ""}
            onClick={() => setParams({ tab: x })}
          >
            {label}
          </button>
        ))}
      </nav>
      <Queue key={type} type={type} />
    </>
  );
}

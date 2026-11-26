import { Link, useSearchParams } from "react-router-dom";
import { labels, post } from "../api";
import { useAuth } from "../auth";
import { useAction, useResource } from "../hooks";
import {
  Badge,
  Empty,
  Feedback,
  PageHead,
  ProjectCard,
  Resource,
} from "../components/ui";

const tabs = [
  ["teams", "Мои команды"],
  ["projects", "Мои проекты"],
  ["applications", "Мои отклики"],
  ["reports", "Мои жалобы"],
  ["notices", "Уведомления"],
];
function Content({ tab }) {
  const state = useResource(`/me/${tab}`);
  const action = useAction();
  return (
    <>
      <Feedback {...action} />
      <Resource state={state}>
        {(items) => {
          if (!items.length)
            return (
              <Empty title="Здесь пока пусто">
                <p>
                  {tab === "teams"
                    ? "Когда автор примет твой отклик, проект появится здесь."
                    : "Все новые записи появятся в этом разделе."}
                </p>
                <Link to="/" className="button secondary">
                  Посмотреть проекты
                </Link>
              </Empty>
            );
          if (tab === "teams" || tab === "projects")
            return (
              <div className="project-grid three">
                {items.map((p) => (
                  <ProjectCard
                    key={p.id}
                    project={p}
                    manage={tab === "projects"}
                  />
                ))}
              </div>
            );
          return (
            <div className="panel list">
              {items.map((item) => (
                <article className="list-item" key={item.id}>
                  {tab === "applications" ? (
                    <>
                      <div className="row spread">
                        <Link to={`/projects/${item.project_id}`}>
                          <h3>{item.project_title}</h3>
                        </Link>
                        <Badge status={item.status} />
                      </div>
                      <p className="muted small">{item.vacancy_title}</p>
                      <p className="pre-wrap">{item.message}</p>
                      {item.status === "pending" && (
                        <button
                          className="text-button danger"
                          disabled={action.busy}
                          onClick={() =>
                            action.run(async () => {
                              await post(`/applications/${item.id}/withdraw`);
                              state.reload();
                            }, "Отклик отозван")
                          }
                        >
                          Отозвать отклик
                        </button>
                      )}
                    </>
                  ) : tab === "reports" ? (
                    <>
                      <div className="row spread">
                        <h3>{item.target_name}</h3>
                        <Badge status={item.status} />
                      </div>
                      <p>
                        {labels[item.reason]} ·{" "}
                        {new Date(item.created_at * 1000).toLocaleDateString(
                          "ru-RU",
                        )}
                      </p>
                      <p className="pre-wrap">{item.message}</p>
                      {item.resolution && (
                        <div className="notice">Решение: {item.resolution}</div>
                      )}
                    </>
                  ) : (
                    <>
                      <h3>{labels[item.action] || item.action}</h3>
                      <p className="pre-wrap">{item.note}</p>
                      <small className="muted">
                        {new Date(item.created_at * 1000).toLocaleString(
                          "ru-RU",
                        )}
                      </small>
                    </>
                  )}
                </article>
              ))}
            </div>
          );
        }}
      </Resource>
    </>
  );
}
export default function Dashboard() {
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const tab = tabs.some(([t]) => t === params.get("tab"))
    ? params.get("tab")
    : "teams";
  return (
    <>
      <PageHead
        eyebrow="ТВОЁ ПРОСТРАНСТВО"
        title={`Привет, ${user.name.split(" ")[0]}`}
        description="Идеи, люди и следующие шаги — всё в одном месте."
      >
        <Link to="/projects/new" className="button">
          + Создать проект
        </Link>
      </PageHead>
      <nav className="tabs" aria-label="Разделы кабинета">
        {tabs.map(([value, label]) => (
          <button
            key={value}
            className={tab === value ? "active" : ""}
            onClick={() => setParams({ tab: value })}
          >
            {label}
          </button>
        ))}
      </nav>
      <Content key={tab} tab={tab} />
    </>
  );
}

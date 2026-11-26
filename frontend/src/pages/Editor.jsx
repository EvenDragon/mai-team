import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { categories, formats, post, put, splitSkills } from "../api";
import { useAuth } from "../auth";
import { useAction, useResource } from "../hooks";
import { Feedback, PageHead, Resource } from "../components/ui";

let nextRoleKey = 0;
const emptyRole = () => ({
  title: "",
  requirements: "",
  capacity: 1,
  key: `draft-${++nextRoleKey}`,
});
function EditorForm({ project }) {
  const [roles, setRoles] = useState(
    project
      ? project.vacancies.map((v) => ({ ...v, key: String(v.id) }))
      : [emptyRole()],
  );
  const action = useAction();
  const navigate = useNavigate();
  const { user } = useAuth();
  if (project && project.owner_id !== user.id)
    return (
      <div className="empty">Редактировать проект может только его автор.</div>
    );
  if (project?.status === "hidden")
    return (
      <div className="empty">
        <h2>Проект скрыт модератором</h2>
        <p>{project.moderation_note}</p>
        <p>Он находится в очереди повторной проверки.</p>
      </div>
    );
  function changeRole(key, name, value) {
    setRoles((current) =>
      current.map((v) => (v.key === key ? { ...v, [name]: value } : v)),
    );
  }
  function submit(e) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const data = {
      title: f.get("title"),
      description: f.get("description"),
      category: f.get("category"),
      format: f.get("format"),
      skills: splitSkills(f.get("skills")),
      team_contact: f.get("team_contact"),
      vacancies: roles.map(({ id, title, requirements, capacity }) => ({
        ...(id ? { id } : {}),
        title,
        requirements,
        capacity: Number(capacity),
      })),
    };
    action.run(async () => {
      const saved = project
        ? await put(`/projects/${project.id}`, data)
        : await post("/projects", data);
      navigate(`/projects/${saved.id}`);
    });
  }
  return (
    <div className="narrow wide-form">
      <PageHead
        eyebrow="ОТ ИДЕИ К КОМАНДЕ"
        title={project ? "Редактировать проект" : "Расскажи о своей идее"}
        description="Понятные задачи помогают найти людей, которым интересно то же, что и тебе."
      />
      <form className="form-stack" onSubmit={submit}>
        <Feedback {...action} />
        <section className="panel">
          <h2>
            <span className="step">01</span> О проекте
          </h2>
          <label>
            Название
            <input
              name="title"
              defaultValue={project?.title}
              required
              minLength={3}
              maxLength={160}
              placeholder="Коротко и по существу"
            />
          </label>
          <label>
            Идея и задачи
            <textarea
              name="description"
              defaultValue={project?.description}
              rows={7}
              minLength={30}
              maxLength={10000}
              required
              placeholder="Что вы хотите сделать, кому это поможет и что получится в итоге? Добавьте сроки и примерную занятость."
            />
          </label>
          <div className="form-grid">
            <label>
              Направление
              <select
                name="category"
                defaultValue={project?.category || categories[0]}
              >
                {categories.map((x) => (
                  <option key={x}>{x}</option>
                ))}
              </select>
            </label>
            <label>
              Формат
              <select
                name="format"
                defaultValue={project?.format || formats[0]}
              >
                {formats.map((x) => (
                  <option key={x}>{x}</option>
                ))}
              </select>
            </label>
          </div>
          <label>
            Навыки через запятую
            <input
              name="skills"
              defaultValue={project?.skills.join(", ")}
              placeholder="Python, исследование, дизайн"
            />
            <small>До 20 навыков, каждый до 40 символов</small>
          </label>
        </section>
        <section className="panel">
          <h2>
            <span className="step">02</span> Кого ты ищешь
          </h2>
          <p className="muted">
            Опиши конкретные задачи и нужный уровень. Если готов помочь новичку
            — напиши об этом.
          </p>
          {roles.map((v, i) => (
            <div className="role-editor" key={v.key}>
              <div className="row spread">
                <h3>Роль {i + 1}</h3>
                <button
                  type="button"
                  className="text-button danger"
                  disabled={roles.length === 1 || !!v.filled}
                  onClick={() =>
                    setRoles((current) =>
                      current.filter((x) => x.key !== v.key),
                    )
                  }
                >
                  Убрать роль
                </button>
              </div>
              <div className="form-grid">
                <label>
                  Название роли
                  <input
                    value={v.title}
                    minLength={2}
                    maxLength={100}
                    required
                    onChange={(e) => changeRole(v.key, "title", e.target.value)}
                  />
                </label>
                <label>
                  Количество мест
                  <input
                    type="number"
                    value={v.capacity}
                    min={Math.max(1, v.filled || 0)}
                    max={30}
                    required
                    onChange={(e) =>
                      changeRole(v.key, "capacity", e.target.value)
                    }
                  />
                </label>
              </div>
              <label>
                Задачи и требования
                <textarea
                  value={v.requirements}
                  required
                  minLength={3}
                  maxLength={2000}
                  rows={3}
                  onChange={(e) =>
                    changeRole(v.key, "requirements", e.target.value)
                  }
                />
              </label>
            </div>
          ))}
          <button
            type="button"
            className="button secondary"
            disabled={roles.length >= 15}
            onClick={() => setRoles((current) => [...current, emptyRole()])}
          >
            + Добавить роль
          </button>
          {project && (
            <p className="small muted">
              Роль с откликами нельзя удалить. Существующие отклики и участники
              сохраняются.
            </p>
          )}
        </section>
        <section className="panel">
          <h2>
            <span className="step">03</span> Как связаться
          </h2>
          <label>
            Telegram команды или автора
            <input
              name="team_contact"
              type="url"
              defaultValue={project?.team_contact}
              maxLength={500}
              required
              pattern="https://t\.me/.+"
              placeholder="https://t.me/…"
            />
            <small>Ссылку увидят только принятые участники и модераторы.</small>
          </label>
        </section>
        <div className="notice">
          После сохранения проект отправится на модерацию. При редактировании он
          временно исчезнет из каталога, но останется доступен команде.
        </div>
        <Feedback {...action} />
        <div className="actions">
          <button className="button" disabled={action.busy}>
            {action.busy ? "Сохраняем…" : "Отправить на проверку ↗"}
          </button>
          <Link
            className="button secondary"
            to={project ? `/projects/${project.id}` : "/dashboard"}
          >
            Отмена
          </Link>
        </div>
      </form>
    </div>
  );
}
function ExistingEditor({ id }) {
  const state = useResource(`/projects/${id}`);
  return <Resource state={state}>{(p) => <EditorForm project={p} />}</Resource>;
}
export default function Editor() {
  const { id } = useParams();
  return id ? <ExistingEditor id={id} /> : <EditorForm />;
}

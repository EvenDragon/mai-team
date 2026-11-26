import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { post, put, splitSkills } from "../api";
import { useAuth } from "../auth";
import { useAction, useResource } from "../hooks";
import {
  Feedback,
  PageHead,
  ReportForm,
  Resource,
  Skills,
} from "../components/ui";

export function AuthPage({ register = false }) {
  const auth = useAuth();
  const action = useAction();
  const navigate = useNavigate();
  const location = useLocation();
  function submit(e) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const data = {
      email: f.get("email"),
      password: f.get("password"),
      ...(register
        ? { name: f.get("name"), accepted_terms: f.has("accepted_terms") }
        : {}),
    };
    action.run(async () => {
      const result = await post(
        register ? "/auth/register" : "/auth/login",
        data,
      );
      await auth.login(result.access_token);
      navigate(location.state?.from || "/dashboard", { replace: true });
    });
  }
  return (
    <div className="auth-layout">
      <div className="auth-story">
        <p className="eyebrow">МАИ.КОМАНДА</p>
        <h1>
          Большие дела
          <br />
          делают вместе.
        </h1>
        <p>
          Разработка, инженерия, наука или помощь людям — найди тех, с кем тебе
          по пути.
        </p>
        <div className="auth-art" aria-hidden="true">
          ✳
        </div>
      </div>
      <form className="panel auth-form" onSubmit={submit}>
        <h2>{register ? "Присоединиться" : "С возвращением"}</h2>
        <p className="muted">
          {register
            ? "Создай аккаунт и найди свою команду."
            : "Твои проекты и команды уже здесь."}
        </p>
        <Feedback error={action.error || auth.error} />
        {register && (
          <label>
            Имя
            <input
              name="name"
              autoComplete="name"
              required
              minLength={2}
              maxLength={100}
            />
          </label>
        )}
        <label>
          Email
          <input
            name="email"
            type="email"
            autoComplete="email"
            required
            maxLength={254}
          />
        </label>
        <label>
          Пароль
          <input
            name="password"
            type="password"
            autoComplete={register ? "new-password" : "current-password"}
            minLength={10}
            maxLength={128}
            required
          />
          <small>От 10 символов</small>
        </label>
        {register && (
          <label className="checkbox">
            <input type="checkbox" name="accepted_terms" required />
            <span>
              Я принимаю{" "}
              <Link to="/rules" target="_blank" rel="noopener noreferrer">
                пользовательское соглашение
              </Link>
            </span>
          </label>
        )}
        <button className="button full" disabled={action.busy}>
          {action.busy ? "Подождите…" : register ? "Создать аккаунт" : "Войти"}
        </button>
        <p className="small">
          {register ? "Уже есть аккаунт? " : "Первый раз здесь? "}
          <Link to={register ? "/login" : "/register"} state={location.state}>
            {register ? "Войти" : "Зарегистрироваться"}
          </Link>
        </p>
      </form>
    </div>
  );
}

export function Profile() {
  const auth = useAuth();
  const action = useAction();
  const u = auth.user;
  return (
    <div className="narrow">
      <PageHead
        eyebrow="ЛИЧНЫЙ КАБИНЕТ"
        title="Мой профиль"
        description="Расскажи, что тебе интересно и чему хочется научиться."
      />
      <form
        className="panel form-stack"
        onSubmit={(e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          action.run(async () => {
            await put("/me", {
              name: f.get("name"),
              institute: f.get("institute"),
              bio: f.get("bio"),
              skills: splitSkills(f.get("skills")),
            });
            await auth.refresh();
          }, "Профиль сохранён");
        }}
      >
        <Feedback {...action} />
        <label>
          Имя
          <input
            name="name"
            defaultValue={u.name}
            minLength={2}
            maxLength={100}
            required
          />
        </label>
        <label>
          Институт и группа
          <input
            name="institute"
            defaultValue={u.institute}
            maxLength={100}
            placeholder="Например, институт № 3, группа…"
          />
        </label>
        <label>
          О себе
          <textarea
            name="bio"
            rows={5}
            maxLength={3000}
            defaultValue={u.bio}
            placeholder="Что умеешь, что интересно, чему хочешь научиться"
          />
        </label>
        <label>
          Навыки через запятую
          <input
            name="skills"
            defaultValue={u.skills.join(", ")}
            placeholder="Python, дизайн, организация"
          />
          <small>До 20 навыков, каждый до 40 символов</small>
        </label>
        <p className="small muted">
          Email: {u.email}. Он не показывается другим участникам.
        </p>
        <button className="button" disabled={action.busy}>
          Сохранить профиль
        </button>
      </form>
    </div>
  );
}

export function PublicProfile() {
  const { id } = useParams();
  const state = useResource(`/users/${id}`);
  const { user } = useAuth();
  return (
    <Resource state={state}>
      {(u) => (
        <div className="narrow">
          <PageHead
            eyebrow="УЧАСТНИК СООБЩЕСТВА"
            title={u.name}
            description={u.institute || "Институт не указан"}
          />
          <section className="panel">
            <div className="avatar large">{u.name[0]}</div>
            <h2>О себе</h2>
            <p className="pre-wrap">
              {u.bio || "Пока ничего не рассказал о себе."}
            </p>
            <h3>Навыки и интересы</h3>
            {u.skills.length ? (
              <Skills items={u.skills} />
            ) : (
              <p className="muted">Навыки пока не указаны.</p>
            )}
          </section>
          {user?.id !== u.id && (
            <ReportForm targetType="user" targetId={u.id} />
          )}
        </div>
      )}
    </Resource>
  );
}

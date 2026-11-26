import { Link, useSearchParams } from "react-router-dom";
import { categories, formats } from "../api";
import { useResource } from "../hooks";
import { Empty, ProjectCard, Resource } from "../components/ui";

export default function Catalog() {
  const [params, setParams] = useSearchParams();
  const projects = useResource(`/projects?${params}`);
  const stats = useResource("/stats");
  function change(name, value) {
    const next = new URLSearchParams(params);
    value ? next.set(name, value) : next.delete(name);
    next.delete("page");
    setParams(next);
  }
  const page = Number(params.get("page")) || 1;
  return (
    <>
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">
            <span className="live-dot" /> СООБЩЕСТВО СТУДЕНТОВ МАИ
          </p>
          <h1>
            Твоя идея.
            <br />
            Ваша <span>команда.</span>
          </h1>
          <p>
            Найди проект по интересам или людей,
            <br className="desktop-only" /> с которыми хочется создавать новое.
          </p>
          <div className="hero-actions">
            <a className="button" href="#catalog">
              Найти проект <span>↓</span>
            </a>
            <Link className="button secondary" to="/projects/new">
              Предложить идею ↗
            </Link>
          </div>
          <p className="hero-caption">
            Первый проект? Здесь можно начать с того, что уже умеешь.
          </p>
        </div>
        <div className="orbit-art" aria-hidden="true">
          <div className="orbit orbit-one" />
          <div className="orbit orbit-two" />
          <div className="orbit-core">
            м<span>✳</span>
          </div>
          <div className="orbit-note note-one">
            <span className="mini-icon">⌘</span>
            <div>
              Твой навык<strong>Часть большого дела</strong>
            </div>
          </div>
          <div className="orbit-note note-two">
            <span className="mini-icon lime">↗</span>
            <div>
              Общая идея<strong>Начало новой команды</strong>
            </div>
          </div>
          <span className="satellite s-one" />
          <span className="satellite s-two" />
          <span className="art-label">НА ОДНОЙ ОРБИТЕ</span>
        </div>
      </section>
      {stats.data && (
        <div className="stats-strip">
          <div>
            <strong>{stats.data.projects}</strong>
            <span>проектов в каталоге</span>
          </div>
          <div>
            <strong>{stats.data.open_places}</strong>
            <span>свободных мест</span>
          </div>
          <div>
            <strong>{stats.data.participants}</strong>
            <span>участников в командах</span>
          </div>
          <p>
            От первой идеи
            <br />
            <b>до общего результата</b> ↗
          </p>
        </div>
      )}
      <section id="catalog" className="catalog-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">НАЙДИ СВОЁ НАПРАВЛЕНИЕ</p>
            <h2>Проекты, которым нужны люди</h2>
          </div>
        </div>
        <form
          className="search"
          key={params.get("q") || ""}
          onSubmit={(e) => {
            e.preventDefault();
            change("q", new FormData(e.currentTarget).get("q"));
          }}
        >
          <span aria-hidden="true">⌕</span>
          <input
            name="q"
            aria-label="Поиск проектов"
            placeholder="Название, идея или задача проекта"
            defaultValue={params.get("q") || ""}
            maxLength={160}
          />
          <button className="button">Найти</button>
        </form>
        <div className="catalog-layout">
          <aside className="filters">
            <div className="filter-title">
              <h3>Фильтры</h3>
              <button className="text-button" onClick={() => setParams({})}>
                Сбросить
              </button>
            </div>
            <label>
              Направление
              <select
                value={params.get("category") || ""}
                onChange={(e) => change("category", e.target.value)}
              >
                <option value="">Все направления</option>
                {categories.map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            </label>
            <label>
              Формат участия
              <select
                value={params.get("format") || ""}
                onChange={(e) => change("format", e.target.value)}
              >
                <option value="">Любой формат</option>
                {formats.map((f) => (
                  <option key={f}>{f}</option>
                ))}
              </select>
            </label>
            <form
              key={params.get("skill") || ""}
              onSubmit={(e) => {
                e.preventDefault();
                change("skill", new FormData(e.currentTarget).get("skill"));
              }}
            >
              <label>
                Навык
                <input
                  name="skill"
                  placeholder="Например, Python"
                  defaultValue={params.get("skill") || ""}
                  maxLength={40}
                />
              </label>
              <button className="text-button">Применить навык →</button>
            </form>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={params.get("open_only") === "true"}
                onChange={(e) =>
                  change("open_only", e.target.checked ? "true" : "")
                }
              />
              Есть свободные места
            </label>
            <div className="filter-tip">
              <span>✳</span>
              <h4>Опыт — не главное</h4>
              <p>
                Смотри требования к роли. Многие команды готовы учиться вместе.
              </p>
            </div>
          </aside>
          <div>
            <Resource state={projects}>
              {(data) => (
                <>
                  <div className="results-bar">
                    <span>
                      Найдено проектов: <strong>{data.total}</strong>
                    </span>
                    <span>Сначала новые</span>
                  </div>
                  {data.items.length ? (
                    <div className="project-grid">
                      {data.items.map((p) => (
                        <ProjectCard key={p.id} project={p} />
                      ))}
                    </div>
                  ) : (
                    <Empty
                      title={
                        data.total
                          ? "На этой странице нет проектов"
                          : "Пока ничего не найдено"
                      }
                    >
                      <p>Попробуй изменить фильтры или предложи свою идею.</p>
                      <Link to="/projects/new" className="button secondary">
                        Создать проект
                      </Link>
                    </Empty>
                  )}
                  {data.pages > 1 && (
                    <nav className="pagination" aria-label="Страницы каталога">
                      <button
                        className="button secondary"
                        disabled={page <= 1}
                        onClick={() => {
                          const n = new URLSearchParams(params);
                          n.set("page", page - 1);
                          setParams(n);
                        }}
                      >
                        ← Назад
                      </button>
                      <span>
                        {page} / {data.pages}
                      </span>
                      <button
                        className="button secondary"
                        disabled={page >= data.pages}
                        onClick={() => {
                          const n = new URLSearchParams(params);
                          n.set("page", page + 1);
                          setParams(n);
                        }}
                      >
                        Дальше →
                      </button>
                    </nav>
                  )}
                </>
              )}
            </Resource>
          </div>
        </div>
      </section>
      <section className="bottom-callout">
        <div>
          <p className="eyebrow">ЕСТЬ ИДЕЯ?</p>
          <h2>Всё начинается с первого человека.</h2>
          <p>Расскажи, что хочешь сделать и какая помощь тебе нужна.</p>
        </div>
        <Link className="button" to="/projects/new">
          Собрать команду ↗
        </Link>
      </section>
    </>
  );
}

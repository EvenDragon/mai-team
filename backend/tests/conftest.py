import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DATABASE_URL", "sqlite://")
from app.db import Base, get_db
from app.main import app
from app.services import attempts
from app.models import User


@pytest.fixture()
def client():
    url = os.getenv("TEST_DATABASE_URL", "sqlite://")
    if not url.startswith("sqlite"):
        if os.getenv("ALLOW_TEST_DB_RESET") != "true" or not url.rsplit("/", 1)[
            -1
        ].endswith("_test"):
            raise RuntimeError(
                "Only a dedicated *_test database with ALLOW_TEST_DB_RESET=true may be reset"
            )
        import psycopg
        from app.migrate import ROOT

        with psycopg.connect(
            url.replace("postgresql+psycopg://", "postgresql://"), autocommit=True
        ) as c:
            c.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public")
            for p in sorted((ROOT / "migrations").glob("*.sql")):
                c.execute(p.read_text(encoding="utf-8-sig"))
        engine = create_engine(url)
    else:
        engine = create_engine(
            url, connect_args={"check_same_thread": False}, poolclass=StaticPool
        )

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

        Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)

    def override():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override
    attempts.clear()
    with TestClient(app) as c:
        c.factory = factory
        yield c
    app.dependency_overrides.clear()
    engine.dispose()


def account(c, email="owner@example.com", role="student"):
    response = c.post(
        "/auth/register",
        json={
            "name": "Тестовый пользователь",
            "email": email,
            "password": "TestPassword2026!",
        },
    )
    assert response.status_code == 201, response.text
    if role != "student":
        with c.factory() as db:
            from sqlalchemy import select

            u = db.scalar(select(User).where(User.email == email))
            u.role = role
            db.commit()
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def payload():
    return {
        "title": "Учебный проект",
        "description": "Достаточно подробное описание учебного проекта и ожидаемых задач для команды.",
        "category": "IT",
        "format": "Онлайн",
        "skills": ["Python"],
        "vacancies": [
            {"title": "Разработчик", "requirements": "Основы Python", "capacity": 1}
        ],
    }


def published(c):
    owner = account(c)
    mod = account(c, "mod@example.com", "moderator")
    p = c.post("/projects", headers=owner, json=payload()).json()
    response = c.post(
        f"/moderation/projects/{p['id']}",
        headers=mod,
        json={"status": "published", "note": "Проверено"},
    )
    assert response.status_code == 200, response.text
    return owner, mod, response.json()

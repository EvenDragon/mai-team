"""Upgrade an old database without losing teams, then rerun the migration runner."""

import hashlib
import os
import pytest


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL", "").startswith("postgresql"),
    reason="PostgreSQL migrations required",
)
def test_upgrade_preserves_legacy_team(monkeypatch):
    import psycopg
    import app.migrate as migration

    url = os.environ["TEST_DATABASE_URL"]
    if os.getenv("ALLOW_TEST_DB_RESET") != "true" or not url.rsplit("/", 1)[
        -1
    ].endswith("_test"):
        raise RuntimeError("Only an explicitly disposable *_test database may be reset")
    sql = (migration.ROOT / "migrations/001_initial.sql").read_text(
        encoding="utf-8-sig"
    )
    pg_url = url.replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(pg_url, autocommit=True) as db:
        db.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public")
        db.execute(sql)
        db.execute(
            "CREATE TABLE schema_migrations(version text PRIMARY KEY, checksum text NOT NULL)"
        )
        db.execute(
            "INSERT INTO schema_migrations VALUES (%s,%s)",
            ("001_initial.sql", hashlib.sha256(sql.encode()).hexdigest()),
        )
        db.execute(
            "INSERT INTO users(id,email,password_hash,name) VALUES (1,'owner@example.com','test','Owner'),(2,'member@example.com','test','Member')"
        )
        db.execute(
            "INSERT INTO projects(id,owner_id,title,description,category,format,status) VALUES (1,1,'Legacy','Legacy project','IT','Онлайн','closed')"
        )
        db.execute(
            "INSERT INTO vacancies(id,project_id,title,requirements,capacity) VALUES (1,1,'Developer','Python',1)"
        )
        db.execute(
            "INSERT INTO applications(id,vacancy_id,user_id,message,status) VALUES (1,1,2,'Accepted member','accepted')"
        )
    monkeypatch.setenv("DATABASE_URL", url)
    migration.migrate()
    migration.migrate()
    with psycopg.connect(pg_url) as db:
        assert db.execute(
            "SELECT status,recruitment_open FROM projects WHERE id=1"
        ).fetchone() == ("pending", False)
        assert db.execute(
            "SELECT user_id,status FROM applications WHERE id=1"
        ).fetchone() == (2, "accepted")
        assert db.execute("SELECT count(*) FROM schema_migrations").fetchone() == (2,)

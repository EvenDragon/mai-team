from concurrent.futures import ThreadPoolExecutor
import os
import pytest
from sqlalchemy import event, select
from conftest import account, published, payload
from app.models import Application, ModerationEvent, Project, User, Vacancy


def test_concurrent_auth_throttle(client):
    from types import SimpleNamespace
    from fastapi import HTTPException
    from app.services import throttle

    request = SimpleNamespace(client=SimpleNamespace(host="parallel-login"))

    def attempt(_):
        try:
            throttle(request)
            return 200
        except HTTPException as error:
            return error.status_code

    with ThreadPoolExecutor(12) as pool:
        codes = list(pool.map(attempt, range(100)))
    assert codes.count(200) == 30
    assert codes.count(429) == 70


def join(c, owner, p, email="member@example.com"):
    h = account(c, email)
    a = c.post(
        f"/vacancies/{p['vacancies'][0]['id']}/applications",
        headers=h,
        json={"message": "Хочу помочь команде с разработкой"},
    ).json()
    assert (
        c.post(
            f"/applications/{a['id']}/decision",
            headers=owner,
            json={"status": "accepted"},
        ).status_code
        == 200
    )
    return h, a


def test_team_access_and_contact_privacy(client):
    owner, mod, p = published(client)
    data = payload()
    data["vacancies"][0]["id"] = p["vacancies"][0]["id"]
    data["team_contact"] = "https://t.me/test_team"
    client.put(f"/projects/{p['id']}", headers=owner, json=data)
    client.post(
        f"/moderation/projects/{p['id']}",
        headers=mod,
        json={"status": "published", "note": "Приватное объяснение автору"},
    )
    member, _ = join(client, owner, p)
    outsider = account(client, "outsider@example.com")
    public = client.get(f"/projects/{p['id']}").json()
    assert public["team_contact"] == public["moderation_note"] == ""
    assert client.get("/projects").json()["items"][0]["team_contact"] == ""
    assert (
        client.get(f"/projects/{p['id']}", headers=member).json()["team_contact"]
        == data["team_contact"]
    )
    assert (
        client.get(f"/projects/{p['id']}", headers=member).json()["moderation_note"]
        == ""
    )
    assert (
        client.get(f"/projects/{p['id']}", headers=owner).json()["moderation_note"]
        == "Приватное объяснение автору"
    )
    client.post(f"/projects/{p['id']}/close", headers=owner)
    assert client.get("/me/teams", headers=member).json()[0]["id"] == p["id"]
    assert client.get(f"/projects/{p['id']}", headers=member).status_code == 200
    client.put(f"/projects/{p['id']}", headers=owner, json=data)
    assert client.get(f"/projects/{p['id']}", headers=member).status_code == 200
    assert client.get(f"/projects/{p['id']}", headers=outsider).status_code == 404
    assert client.get(f"/projects/{p['id']}").status_code == 404


def test_withdraw_reapply_leave_and_remove(client):
    owner, _, p = published(client)
    h = account(client, "applicant@example.com")
    v = p["vacancies"][0]["id"]
    path = f"/vacancies/{v}/applications"
    body = {"message": "Помогу с задачами на Python"}
    a = client.post(path, headers=h, json=body).json()
    assert (
        client.post(f"/applications/{a['id']}/withdraw", headers=owner).status_code
        == 403
    )
    assert (
        client.post(f"/applications/{a['id']}/withdraw", headers=h).json()["status"]
        == "withdrawn"
    )
    assert (
        client.post(
            f"/applications/{a['id']}/decision",
            headers=owner,
            json={"status": "accepted"},
        ).status_code
        == 409
    )
    assert client.post(path, headers=h, json=body).json()["id"] == a["id"]
    client.post(
        f"/applications/{a['id']}/decision", headers=owner, json={"status": "accepted"}
    )
    uid = client.get("/me", headers=h).json()["id"]
    assert (
        client.delete(f"/projects/{p['id']}/members/{uid}", headers=h).status_code
        == 200
    )
    assert client.get("/me/teams", headers=h).json() == []
    assert client.post(path, headers=h, json=body).status_code == 201
    client.post(
        f"/applications/{a['id']}/decision", headers=owner, json={"status": "accepted"}
    )
    assert (
        client.delete(f"/projects/{p['id']}/members/{uid}", headers=owner).status_code
        == 200
    )
    assert client.post(path, headers=h, json=body).status_code == 409
    assert client.get(f"/projects/{p['id']}").json()["vacancies"][0]["filled"] == 0


def test_recruitment_reopening_permissions(client):
    owner, _, p = published(client)
    other = account(client, "other@example.com")
    path = f"/projects/{p['id']}/recruitment"
    assert client.post(path, headers=other, json={"open": False}).status_code == 403
    client.post(path, headers=owner, json={"open": False})
    assert client.get("/projects?open_only=true").json()["total"] == 0
    assert client.get("/stats").json()["open_places"] == 0
    assert (
        client.post(path, headers=owner, json={"open": True}).json()["recruitment_open"]
        is True
    )


def test_reports_private_deduplicated_and_audited(client):
    owner, mod, p = published(client)
    reporter = account(client, "reporter@example.com")
    body = {
        "target_type": "project",
        "target_id": p["id"],
        "reason": "spam",
        "message": "Проверить описание",
    }
    r = client.post("/reports", headers=reporter, json=body)
    assert r.status_code == 201 and "reporter_id" not in r.json()
    assert client.post("/reports", headers=reporter, json=body).status_code == 409
    assert client.get("/projects").json()["total"] == 1
    assert client.get("/moderation/reports", headers=owner).status_code == 403
    assert client.get("/me/reports", headers=owner).json() == []
    path = f"/moderation/reports/{r.json()['id']}"
    assert (
        client.post(
            path, headers=owner, json={"action": "hide", "note": "Скрыть спам"}
        ).status_code
        == 403
    )
    assert (
        client.post(
            path,
            headers=mod,
            json={"action": "hide", "note": "Уберите рекламные ссылки"},
        ).status_code
        == 200
    )
    assert client.get("/projects").json()["total"] == 0
    assert (
        client.get(f"/projects/{p['id']}", headers=owner).json()["status"] == "hidden"
    )
    assert client.get("/me/reports", headers=reporter).json()[0]["status"] == "resolved"
    assert (
        client.get("/me/notices", headers=owner).json()[0]["note"]
        == "Уберите рекламные ссылки"
    )
    assert (
        client.post(
            path, headers=mod, json={"action": "dismiss", "note": "Повторное решение"}
        ).status_code
        == 409
    )
    assert len(client.get("/moderation/history", headers=mod).json()) == 2
    assert (
        client.post(
            f"/moderation/projects/{p['id']}",
            headers=mod,
            json={"status": "published", "note": "Повторно проверено"},
        ).status_code
        == 200
    )


def test_user_report_block_revokes_sessions_and_hides_projects(client):
    owner, mod, p = published(client)
    reporter = account(client, "reporter@example.com")
    uid = client.get("/me", headers=owner).json()["id"]
    r = client.post(
        "/reports",
        headers=reporter,
        json={"target_type": "user", "target_id": uid, "reason": "fraud"},
    ).json()
    assert (
        client.post(
            f"/moderation/reports/{r['id']}",
            headers=mod,
            json={"action": "hide", "note": "Некорректное действие"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"/moderation/reports/{r['id']}",
            headers=mod,
            json={"action": "block", "note": "Повторный спам"},
        ).status_code
        == 200
    )
    assert client.get("/me", headers=owner).status_code == 401
    assert (
        client.post(
            "/auth/login",
            json={"email": "owner@example.com", "password": "TestPassword2026!"},
        ).status_code
        == 403
    )
    assert client.get("/projects").json()["total"] == 0
    assert (
        client.post(
            f"/moderation/users/{uid}/block",
            headers=mod,
            json={"blocked": False, "note": "Ошибку исправили"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/auth/login",
            json={"email": "owner@example.com", "password": "TestPassword2026!"},
        ).status_code
        == 200
    )
    assert client.get("/me", headers=owner).status_code == 401
    assert client.get("/projects").json()["total"] == 1


def test_moderation_self_conflicts(client):
    owner, mod, p = published(client)
    uid = client.get("/me", headers=mod).json()["id"]
    assert (
        client.post(
            f"/moderation/users/{uid}/block",
            headers=mod,
            json={"blocked": True, "note": "Самоблокировка"},
        ).status_code
        == 403
    )
    r = client.post(
        "/reports",
        headers=mod,
        json={"target_type": "project", "target_id": p["id"], "reason": "other"},
    ).json()
    assert (
        client.post(
            f"/moderation/reports/{r['id']}",
            headers=mod,
            json={"action": "dismiss", "note": "Моя собственная жалоба"},
        ).status_code
        == 403
    )


@pytest.mark.parametrize(
    "value",
    [
        "javascript:alert(1)",
        "https://t.me.evil.test/chat",
        "http://t.me/chat",
        "https://t.me@evil.test/chat",
    ],
)
def test_contact_url_validation(client, value):
    owner = account(client)
    assert (
        client.post(
            "/projects", headers=owner, json={**payload(), "team_contact": value}
        ).status_code
        == 422
    )


def test_catalog_sql_pagination_and_bounded_queries(client):
    owner, _, p = published(client)
    with client.factory() as db:
        for i in range(30):
            project = Project(
                owner_id=p["owner_id"],
                title=f"Проект {i}",
                description="Описание",
                category="IT",
                format="Онлайн",
                status="published",
            )
            db.add(project)
            db.flush()
            db.add(
                Vacancy(
                    project_id=project.id,
                    title="Роль",
                    requirements="Навыки",
                    capacity=1,
                )
            )
        db.commit()
    statements = []
    engine = client.factory.kw["bind"]

    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        data = client.get("/projects?page=2&open_only=true").json()
    finally:
        event.remove(engine, "before_cursor_execute", record)
    assert data["total"] == 31 and len(data["items"]) == 12 and data["pages"] == 3
    assert len(statements) <= 5


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL", "").startswith("postgresql"),
    reason="PostgreSQL row locks required",
)
def test_concurrent_withdraw_and_accept(client):
    owner, _, p = published(client)
    h = account(client, "student@example.com")
    a = client.post(
        f"/vacancies/{p['vacancies'][0]['id']}/applications",
        headers=h,
        json={"message": "Готов работать с командой"},
    ).json()
    with ThreadPoolExecutor(2) as pool:
        tasks = [
            pool.submit(client.post, f"/applications/{a['id']}/withdraw", headers=h),
            pool.submit(
                client.post,
                f"/applications/{a['id']}/decision",
                headers=owner,
                json={"status": "accepted"},
            ),
        ]
        codes = [t.result().status_code for t in tasks]
    assert sorted(codes) == [200, 409]


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL", "").startswith("postgresql"),
    reason="PostgreSQL row locks required",
)
def test_concurrent_duplicate_reports(client):
    owner, _, p = published(client)
    h = account(client, "reporter@example.com")
    body = {"target_type": "project", "target_id": p["id"], "reason": "other"}
    with ThreadPoolExecutor(2) as pool:
        codes = list(
            pool.map(
                lambda _: client.post("/reports", headers=h, json=body).status_code,
                range(2),
            )
        )
    assert sorted(codes) == [201, 409]

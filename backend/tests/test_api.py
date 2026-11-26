import os
import time
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import select
from conftest import account, published, payload
from app.models import Session, User


def test_registration_profile_logout(client):
    h = account(client)
    me = client.get("/me", headers=h).json()
    assert me["role"] == "student"
    with client.factory() as db:
        assert db.get(User, me["id"]).terms_accepted_at is not None
    data = {
        "name": "Участник команды",
        "bio": "Интересуюсь проектами",
        "institute": "Тестовая группа",
        "skills": ["Python", "Python", "React"],
    }
    r = client.put("/me", headers=h, json=data)
    assert r.status_code == 200 and r.json()["skills"] == ["Python", "React"]
    public = client.get("/users/" + str(me["id"]), headers=h).json()
    assert "email" not in public and "password_hash" not in public
    assert client.post("/auth/logout", headers=h).status_code == 200
    assert client.get("/me", headers=h).status_code == 401


def test_login_and_duplicate(client):
    account(client)
    d = {"email": "owner@example.com", "password": "TestPassword2026!"}
    assert client.post("/auth/login", json=d).status_code == 200
    assert (
        client.post("/auth/login", json={**d, "password": "WrongPassword!"}).status_code
        == 401
    )
    duplicate = {**d, "name": "Другой", "accepted_terms": True}
    assert client.post("/auth/register", json=duplicate).status_code == 409


@pytest.mark.parametrize(
    "data",
    [
        {"email": "bad", "name": "OK", "password": "TestPassword2026!"},
        {"email": "x@example.com", "name": "a", "password": "x"},
        {
            "email": "x@example.com",
            "name": "User",
            "password": "TestPassword2026!",
            "role": "moderator",
        },
    ],
)
def test_registration_validation(client, data):
    assert client.post("/auth/register", json={**data, "accepted_terms": True}).status_code == 422


@pytest.mark.parametrize(
    "consent",
    [{}, {"accepted_terms": False}, {"accepted_terms": "true"}, {"accepted_terms": 1}],
)
def test_registration_requires_explicit_consent(client, consent):
    data = {"email": "new@example.com", "name": "Student", "password": "TestPassword2026!"}
    assert client.post("/auth/register", json={**data, **consent}).status_code == 422
    with client.factory() as db:
        assert db.scalar(select(User)) is None


def test_session_expiry(client):
    h = account(client)
    with client.factory() as db:
        s = db.scalar(select(Session))
        s.expires_at = int(time.time()) - 1
        db.commit()
    assert client.get("/me", headers=h).status_code == 401


def test_moderation_visibility_and_rights(client):
    owner = account(client)
    other = account(client, "other@example.com")
    mod = account(client, "mod@example.com", "moderator")
    p = client.post("/projects", headers=owner, json=payload()).json()
    pid = p["id"]
    assert p["status"] == "pending"
    assert client.get("/projects").json()["total"] == 0
    assert client.get(f"/projects/{pid}", headers=other).status_code == 404
    assert client.get("/moderation/projects", headers=owner).status_code == 403
    assert (
        client.post(
            f"/moderation/projects/{pid}",
            headers=owner,
            json={"status": "published", "note": "test"},
        ).status_code
        == 403
    )
    assert (
        client.put(f"/projects/{pid}", headers=other, json=payload()).status_code == 403
    )
    assert (
        client.post(
            f"/moderation/projects/{pid}",
            headers=mod,
            json={"status": "rejected", "note": "Добавьте подробности"},
        ).status_code
        == 200
    )
    assert (
        client.put(f"/projects/{pid}", headers=owner, json=payload()).json()["status"]
        == "pending"
    )
    assert (
        client.post(
            f"/moderation/projects/{pid}",
            headers=mod,
            json={"status": "published", "note": "Проверено"},
        ).status_code
        == 200
    )
    assert client.get("/projects").json()["total"] == 1


def test_full_application_and_team_flow(client):
    owner, mod, p = published(client)
    student = account(client, "student@example.com")
    v = p["vacancies"][0]["id"]
    pid = p["id"]
    r = client.post(
        f"/vacancies/{v}/applications",
        headers=student,
        json={"message": "Хочу участвовать и развивать навыки Python"},
    )
    assert r.status_code == 201
    aid = r.json()["id"]
    assert (
        client.post(
            f"/vacancies/{v}/applications",
            headers=student,
            json={"message": "Повторный отклик на ту же роль"},
        ).status_code
        == 409
    )
    assert (
        client.get(f"/projects/{pid}/applications", headers=student).status_code == 403
    )
    assert (
        client.post(
            f"/applications/{aid}/decision",
            headers=student,
            json={"status": "accepted"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/applications/{aid}/decision", headers=owner, json={"status": "accepted"}
        ).status_code
        == 200
    )
    team = client.get(f"/projects/{pid}").json()
    assert len(team["team"]) == 1 and team["vacancies"][0]["filled"] == 1
    assert (
        client.get("/me/applications", headers=student).json()[0]["status"]
        == "accepted"
    )
    assert client.get("/stats").json() == {
        "projects": 1,
        "participants": 1,
        "open_places": 0,
    }
    assert (
        client.post(
            f"/applications/{aid}/decision", headers=owner, json={"status": "rejected"}
        ).status_code
        == 409
    )


def test_no_overbooking(client):
    owner, _, p = published(client)
    v = p["vacancies"][0]["id"]
    ids = []
    for i in range(2):
        h = account(client, f"s{i}@example.com")
        ids.append(
            client.post(
                f"/vacancies/{v}/applications",
                headers=h,
                json={"message": "Хочу помочь с разработкой проекта"},
            ).json()["id"]
        )
    assert (
        client.post(
            f"/applications/{ids[0]}/decision",
            headers=owner,
            json={"status": "accepted"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/applications/{ids[1]}/decision",
            headers=owner,
            json={"status": "accepted"},
        ).status_code
        == 409
    )


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL", "").startswith("postgresql"),
    reason="PostgreSQL row locks required",
)
def test_concurrent_acceptance(client):
    owner, _, p = published(client)
    v = p["vacancies"][0]["id"]
    ids = []
    for i in range(2):
        h = account(client, f"parallel{i}@example.com")
        ids.append(
            client.post(
                f"/vacancies/{v}/applications",
                headers=h,
                json={"message": "Хочу помочь с разработкой проекта"},
            ).json()["id"]
        )
    with ThreadPoolExecutor(2) as pool:
        codes = list(
            pool.map(
                lambda aid: client.post(
                    f"/applications/{aid}/decision",
                    headers=owner,
                    json={"status": "accepted"},
                ).status_code,
                ids,
            )
        )
    assert sorted(codes) == [200, 409]


def test_edit_preserves_applications(client):
    owner, _, p = published(client)
    h = account(client, "student@example.com")
    v = p["vacancies"][0]["id"]
    client.post(
        f"/vacancies/{v}/applications",
        headers=h,
        json={"message": "Готов присоединиться к разработке"},
    )
    data = payload()
    # Replacing a role that already has an application must fail atomically.
    assert (
        client.put(f"/projects/{p['id']}", headers=owner, json=data).status_code == 409
    )
    data["vacancies"][0]["id"] = v
    assert (
        client.put(f"/projects/{p['id']}", headers=owner, json=data).status_code == 200
    )
    assert client.get("/me/applications", headers=h).json()[0]["vacancy_id"] == v
    assert client.get("/projects").json()["total"] == 0


def test_search_and_close(client):
    owner, _, p = published(client)
    assert (
        client.get(
            "/projects?q=Учебный&category=IT&format=Онлайн&skill=Python&open_only=true"
        ).json()["total"]
        == 1
    )
    assert client.get("/projects?q=неттакогопроекта").json()["total"] == 0
    assert client.get("/projects?q=%25").json()["total"] == 0
    assert client.get("/projects?category=Наука").json()["total"] == 0
    assert client.post(f"/projects/{p['id']}/close", headers=owner).status_code == 200
    assert client.get("/projects").json()["total"] == 1
    assert client.get("/projects?open_only=true").json()["total"] == 0


@pytest.mark.parametrize(
    "path,method",
    [
        ("/me", "get"),
        ("/projects", "post"),
        ("/moderation/projects", "get"),
        ("/me/applications", "get"),
    ],
)
def test_auth_required(client, path, method):
    assert (
        getattr(client, method)(
            path, **({"json": payload()} if method == "post" else {})
        ).status_code
        == 401
    )


def test_project_validation_and_mass_assignment(client):
    owner = account(client)
    d = payload()
    assert (
        client.post("/projects", headers=owner, json={**d, "owner_id": 999}).status_code
        == 422
    )
    assert (
        client.post(
            "/projects", headers=owner, json={**d, "status": "published"}
        ).status_code
        == 422
    )
    d["vacancies"][0]["capacity"] = 0
    assert client.post("/projects", headers=owner, json=d).status_code == 422
    assert (
        client.put(
            "/me", headers=owner, json={"name": "Test", "role": "moderator"}
        ).status_code
        == 422
    )


def test_rejection(client):
    owner, _, p = published(client)
    h = account(client, "student@example.com")
    a = client.post(
        f"/vacancies/{p['vacancies'][0]['id']}/applications",
        headers=h,
        json={"message": "Хочу поработать в команде проекта"},
    ).json()
    assert (
        client.post(
            f"/applications/{a['id']}/decision",
            headers=owner,
            json={"status": "rejected"},
        ).json()["status"]
        == "rejected"
    )
    assert client.get(f"/projects/{p['id']}").json()["team"] == []


def test_moderator_cannot_self_approve(client):
    h = account(client, "mod@example.com", "moderator")
    p = client.post("/projects", headers=h, json=payload()).json()
    assert (
        client.post(
            f"/moderation/projects/{p['id']}",
            headers=h,
            json={"status": "published", "note": "Самопроверка"},
        ).status_code
        == 403
    )


def test_capacity_and_role_edit_validation(client):
    owner, mod, p = published(client)
    v = p["vacancies"][0]["id"]
    h = account(client, "student@example.com")
    a = client.post(
        f"/vacancies/{v}/applications",
        headers=h,
        json={"message": "Готов работать над задачами проекта"},
    ).json()
    client.post(
        f"/applications/{a['id']}/decision", headers=owner, json={"status": "accepted"}
    )
    data = payload()
    data["vacancies"][0]["id"] = v
    data["vacancies"].append(
        {"title": "Аналитик", "requirements": "Основы анализа", "capacity": 1}
    )
    updated = client.put(f"/projects/{p['id']}", headers=owner, json=data)
    assert updated.status_code == 200
    client.post(
        f"/moderation/projects/{p['id']}",
        headers=mod,
        json={"status": "published", "note": "Правки проверены"},
    )
    other_role = updated.json()["vacancies"][1]["id"]
    assert (
        client.post(
            f"/vacancies/{other_role}/applications",
            headers=h,
            json={"message": "Уже в команде, повторно нельзя"},
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/vacancies/{v}/applications",
            headers=owner,
            json={"message": "Автор не должен откликаться себе"},
        ).status_code
        == 409
    )


def test_invalid_role_id_and_duplicate_id(client):
    owner, _, p = published(client)
    d = payload()
    d["vacancies"][0]["id"] = 99999
    assert client.put(f"/projects/{p['id']}", headers=owner, json=d).status_code == 422
    d["vacancies"][0]["id"] = p["vacancies"][0]["id"]
    d["vacancies"].append(dict(d["vacancies"][0]))
    assert client.put(f"/projects/{p['id']}", headers=owner, json=d).status_code == 422


def test_closed_project_blocks_decisions_and_applications(client):
    owner, _, p = published(client)
    h = account(client, "student@example.com")
    v = p["vacancies"][0]["id"]
    a = client.post(
        f"/vacancies/{v}/applications",
        headers=h,
        json={"message": "Хочу работать над задачами проекта"},
    ).json()
    client.post(f"/projects/{p['id']}/close", headers=owner)
    assert (
        client.post(
            f"/applications/{a['id']}/decision",
            headers=owner,
            json={"status": "accepted"},
        ).status_code
        == 409
    )
    new = account(client, "new@example.com")
    assert (
        client.post(
            f"/vacancies/{v}/applications",
            headers=new,
            json={"message": "После закрытия отклики запрещены"},
        ).status_code
        == 409
    )


def test_multiple_pending_roles_become_single_membership(client):
    owner = account(client)
    mod = account(client, "mod@example.com", "moderator")
    d = payload()
    d["vacancies"].append(
        {"title": "Дизайнер", "requirements": "Основы Figma", "capacity": 1}
    )
    p = client.post("/projects", headers=owner, json=d).json()
    client.post(
        f"/moderation/projects/{p['id']}",
        headers=mod,
        json={"status": "published", "note": "Проверено"},
    )
    h = account(client, "student@example.com")
    ids = []
    for v in p["vacancies"]:
        ids.append(
            client.post(
                f"/vacancies/{v['id']}/applications",
                headers=h,
                json={"message": "Хочу работать в команде этого проекта"},
            ).json()["id"]
        )
    client.post(
        f"/applications/{ids[0]}/decision", headers=owner, json={"status": "accepted"}
    )
    assert sorted(
        a["status"] for a in client.get("/me/applications", headers=h).json()
    ) == ["accepted", "rejected"]


def test_auth_throttle(client, monkeypatch):
    from collections import deque
    from types import SimpleNamespace
    import app.services as main

    main.attempts["testclient"] = deque([100.0] * 30)
    monkeypatch.setattr(main, "time", SimpleNamespace(monotonic=lambda: 100.0))
    assert (
        client.post(
            "/auth/login",
            json={"email": "none@example.com", "password": "WrongPassword2026!"},
        ).status_code
        == 429
    )

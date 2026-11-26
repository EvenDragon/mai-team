"""Shared presentation and permission rules. Routes own transactions."""

import json
import time
from threading import Lock
from collections import defaultdict, deque
from fastapi import HTTPException
from sqlalchemy import select
from .models import User, Project, Vacancy, Application, ModerationEvent

attempts = defaultdict(deque)
attempts_lock = Lock()


def throttle(request):
    key = request.client.host if request.client else "unknown"
    now = time.monotonic()
    with attempts_lock:
        # Reclaim idle clients; protect check+append across FastAPI worker threads.
        for old_key in list(attempts):
            if not attempts[old_key] or attempts[old_key][-1] < now - 60:
                del attempts[old_key]
        bucket = attempts[key]
        while bucket and bucket[0] < now - 60:
            bucket.popleft()
        if len(bucket) >= 30:
            raise HTTPException(429, "Слишком много попыток. Повторите через минуту.")
        bucket.append(now)


def user_dict(user, private=False):
    data = dict(
        id=user.id,
        name=user.name,
        bio=user.bio,
        institute=user.institute,
        skills=json.loads(user.skills),
        role=user.role,
    )
    if private:
        data["email"] = user.email
    return data


def get_project(db, project_id):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Проект не найден")
    return project


def owner_only(project, user):
    if project.owner_id != user.id:
        raise HTTPException(403, "Только автор проекта может выполнить действие")


def is_member(db, project_id, user_id):
    return (
        db.scalar(
            select(Application.id)
            .join(Vacancy)
            .where(
                Vacancy.project_id == project_id,
                Application.user_id == user_id,
                Application.status == "accepted",
            )
            .limit(1)
        )
        is not None
    )


def projects_dict(db, projects, viewer=None):
    """Batch related rows for the current page, not the entire catalogue."""
    if not projects:
        return []
    ids = [p.id for p in projects]
    owners = {
        u.id: u
        for u in db.scalars(
            select(User).where(User.id.in_({p.owner_id for p in projects}))
        )
    }
    roles = defaultdict(list)
    for vacancy in db.scalars(
        select(Vacancy).where(Vacancy.project_id.in_(ids)).order_by(Vacancy.id)
    ):
        roles[vacancy.project_id].append(vacancy)
    members = defaultdict(list)
    rows = db.execute(
        select(User, Vacancy)
        .join(Application, Application.user_id == User.id)
        .join(Vacancy, Application.vacancy_id == Vacancy.id)
        .where(Vacancy.project_id.in_(ids), Application.status == "accepted")
        .order_by(Application.id)
    )
    for user, vacancy in rows:
        members[vacancy.project_id].append((user, vacancy))
    result = []
    for p in projects:
        team = members[p.id]
        manage = viewer is not None and (
            viewer.id == p.owner_id or viewer.role == "moderator"
        )
        contact_allowed = manage or (
            viewer is not None and any(u.id == viewer.id for u, _ in team)
        )
        result.append(
            dict(
                id=p.id,
                owner_id=p.owner_id,
                owner_name=owners[p.owner_id].name,
                title=p.title,
                description=p.description,
                category=p.category,
                format=p.format,
                skills=json.loads(p.skills),
                status=p.status,
                is_demo=p.is_demo,
                recruitment_open=p.recruitment_open,
                moderation_note=p.moderation_note if manage else "",
                team_contact=p.team_contact if contact_allowed else "",
                vacancies=[
                    dict(
                        id=v.id,
                        title=v.title,
                        requirements=v.requirements,
                        capacity=v.capacity,
                        filled=sum(1 for _, role in team if role.id == v.id),
                    )
                    for v in roles[p.id]
                ],
                team=[dict(id=u.id, name=u.name, vacancy=v.title) for u, v in team],
            )
        )
    return result


def project_dict(db, project, viewer=None):
    return projects_dict(db, [project], viewer)[0]


def application_dict(db, a):
    vacancy = db.get(Vacancy, a.vacancy_id)
    project = db.get(Project, vacancy.project_id)
    return dict(
        id=a.id,
        vacancy_id=a.vacancy_id,
        user_id=a.user_id,
        message=a.message,
        status=a.status,
        applicant=user_dict(db.get(User, a.user_id)),
        project_id=project.id,
        project_title=project.title,
        vacancy_title=vacancy.title,
    )


def audit(db, moderator_id, action, note, **targets):
    db.add(
        ModerationEvent(
            moderator_id=moderator_id,
            action=action,
            note=note,
            created_at=int(time.time()),
            **targets
        )
    )

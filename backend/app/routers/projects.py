import json
import math
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_, exists
from sqlalchemy.orm import Session as DB
from ..db import get_db
from ..models import User, Project, Vacancy, Application
from ..schemas import ProjectInput, ProjectOut, ProjectPage, Recruitment, Stats
from ..security import current_user, bearer
from ..services import get_project, owner_only, project_dict, projects_dict, is_member

router = APIRouter()


@router.get("/stats", response_model=Stats)
def stats(db: DB = Depends(get_db)):
    visible = (
        select(Project.id)
        .join(User, Project.owner_id == User.id)
        .where(Project.status == "published", User.is_blocked == False)
    )
    count = db.scalar(select(func.count()).select_from(visible.subquery()))
    recruiting = visible.where(Project.recruitment_open == True)
    filled = (
        select(func.count(Application.id))
        .where(Application.vacancy_id == Vacancy.id, Application.status == "accepted")
        .correlate(Vacancy)
        .scalar_subquery()
    )
    places = (
        db.scalar(
            select(func.sum(Vacancy.capacity - filled)).where(
                Vacancy.project_id.in_(recruiting)
            )
        )
        or 0
    )
    participants = (
        db.scalar(
            select(func.count(func.distinct(Application.user_id))).where(
                Application.status == "accepted"
            )
        )
        or 0
    )
    return {"projects": count, "open_places": places, "participants": participants}


@router.get("/projects", response_model=ProjectPage)
def catalog(
    q: str = Query("", max_length=160),
    category: str = "",
    format: str = "",
    skill: str = Query("", max_length=40),
    open_only: bool = False,
    page: int = Query(1, ge=1),
    db: DB = Depends(get_db),
):
    query = (
        select(Project)
        .join(User, Project.owner_id == User.id)
        .where(Project.status == "published", User.is_blocked == False)
    )

    # Literal substring search: escape SQL wildcard characters supplied by the user.
    def pattern(s):
        return (
            "%" + s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        )

    if q:
        query = query.where(
            or_(
                Project.title.ilike(pattern(q), escape="\\"),
                Project.description.ilike(pattern(q), escape="\\"),
            )
        )
    if category:
        query = query.where(Project.category == category)
    if format:
        query = query.where(Project.format == format)
    if skill:
        query = query.where(Project.skills.ilike(pattern(skill), escape="\\"))
    if open_only:
        filled = (
            select(func.count(Application.id))
            .where(
                Application.vacancy_id == Vacancy.id, Application.status == "accepted"
            )
            .correlate(Vacancy)
            .scalar_subquery()
        )
        available = exists(
            select(Vacancy.id).where(
                Vacancy.project_id == Project.id, Vacancy.capacity > filled
            )
        )
        query = query.where(Project.recruitment_open == True, available)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    projects = db.scalars(
        query.order_by(Project.id.desc()).offset((page - 1) * 12).limit(12)
    ).all()
    return {
        "items": projects_dict(db, projects),
        "total": total,
        "page": page,
        "pages": math.ceil(total / 12),
    }


@router.get("/me/projects", response_model=list[ProjectOut])
def my_projects(user=Depends(current_user), db: DB = Depends(get_db)):
    return projects_dict(
        db,
        db.scalars(
            select(Project)
            .where(Project.owner_id == user.id)
            .order_by(Project.id.desc())
        ).all(),
        user,
    )


@router.get("/me/teams", response_model=list[ProjectOut])
def my_teams(user=Depends(current_user), db: DB = Depends(get_db)):
    ids = (
        select(Vacancy.project_id)
        .join(Application)
        .where(Application.user_id == user.id, Application.status == "accepted")
    )
    return projects_dict(
        db,
        db.scalars(
            select(Project).where(Project.id.in_(ids)).order_by(Project.id.desc())
        ).all(),
        user,
    )


@router.get("/projects/{project_id}", response_model=ProjectOut)
def detail(project_id: int, db: DB = Depends(get_db), auth=Depends(bearer)):
    p = get_project(db, project_id)
    u = current_user(auth, db) if auth else None
    if p.status != "published" or db.get(User, p.owner_id).is_blocked:
        if not u or not (
            u.id == p.owner_id or u.role == "moderator" or is_member(db, p.id, u.id)
        ):
            raise HTTPException(404, "Проект не найден")
    return project_dict(db, p, u)


@router.post("/projects", response_model=ProjectOut, status_code=201)
def create_project(
    data: ProjectInput, user=Depends(current_user), db: DB = Depends(get_db)
):
    if any(v.id is not None for v in data.vacancies):
        raise HTTPException(422, "Новые роли не должны иметь id")
    p = Project(
        owner_id=user.id,
        **data.model_dump(exclude={"vacancies", "skills"}),
        skills=json.dumps(data.skills, ensure_ascii=False)
    )
    db.add(p)
    db.flush()
    for v in data.vacancies:
        db.add(Vacancy(project_id=p.id, **v.model_dump(exclude={"id"})))
    db.commit()
    return project_dict(db, p, user)


@router.put("/projects/{project_id}", response_model=ProjectOut)
def edit_project(
    project_id: int,
    data: ProjectInput,
    user=Depends(current_user),
    db: DB = Depends(get_db),
):
    # Consistent lock ordering with applications: project first, then vacancy.
    p = db.scalar(select(Project).where(Project.id == project_id).with_for_update())
    if not p:
        raise HTTPException(404, "Проект не найден")
    owner_only(p, user)
    if p.status == "hidden":
        raise HTTPException(
            409, "Проект скрыт модератором. Дождитесь повторной проверки."
        )
    current = {
        v.id: v for v in db.scalars(select(Vacancy).where(Vacancy.project_id == p.id))
    }
    ids = [v.id for v in data.vacancies if v.id is not None]
    if len(ids) != len(set(ids)) or any(i not in current for i in ids):
        raise HTTPException(422, "Некорректные id ролей")
    for vid, v in current.items():
        if vid not in ids:
            if db.scalar(
                select(Application.id).where(Application.vacancy_id == vid).limit(1)
            ):
                raise HTTPException(
                    409, "Роль с откликами нельзя удалить; сохраните её в проекте"
                )
            db.delete(v)
    for v in data.vacancies:
        if v.id:
            filled = db.scalar(
                select(func.count())
                .select_from(Application)
                .where(Application.vacancy_id == v.id, Application.status == "accepted")
            )
            if v.capacity < filled:
                raise HTTPException(409, "Вместимость меньше уже принятой команды")
            for k, val in v.model_dump(exclude={"id"}).items():
                setattr(current[v.id], k, val)
        else:
            db.add(Vacancy(project_id=p.id, **v.model_dump(exclude={"id"})))
    for k, val in data.model_dump(exclude={"vacancies", "skills"}).items():
        setattr(p, k, val)
    p.skills = json.dumps(data.skills, ensure_ascii=False)
    p.status = "pending"
    p.moderation_note = ""
    db.commit()
    return project_dict(db, p, user)


@router.post("/projects/{project_id}/close", response_model=ProjectOut)
def close_project(
    project_id: int, user=Depends(current_user), db: DB = Depends(get_db)
):
    p = db.scalar(select(Project).where(Project.id == project_id).with_for_update())
    if not p:
        raise HTTPException(404, "Проект не найден")
    owner_only(p, user)
    p.recruitment_open = False
    db.commit()
    return project_dict(db, p, user)


@router.post("/projects/{project_id}/recruitment", response_model=ProjectOut)
def recruitment(
    project_id: int,
    data: Recruitment,
    user=Depends(current_user),
    db: DB = Depends(get_db),
):
    p = db.scalar(select(Project).where(Project.id == project_id).with_for_update())
    if not p:
        raise HTTPException(404, "Проект не найден")
    owner_only(p, user)
    if data.open and p.status != "published":
        raise HTTPException(409, "Сначала опубликуйте проект")
    p.recruitment_open = data.open
    db.commit()
    return project_dict(db, p, user)

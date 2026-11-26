from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session as DB
from ..db import get_db
from ..models import User, Project, Vacancy, Application
from ..schemas import ApplicationInput, ApplicationOut, Decision, Message
from ..security import current_user
from ..services import get_project, owner_only, application_dict

router = APIRouter()


@router.post(
    "/vacancies/{vacancy_id}/applications",
    response_model=ApplicationOut,
    status_code=201,
)
def apply(
    vacancy_id: int,
    data: ApplicationInput,
    user=Depends(current_user),
    db: DB = Depends(get_db),
):
    v = db.get(Vacancy, vacancy_id)
    if not v:
        raise HTTPException(404, "Роль не найдена")
    p = db.scalar(select(Project).where(Project.id == v.project_id).with_for_update())
    if (
        p.status != "published"
        or not p.recruitment_open
        or db.get(User, p.owner_id).is_blocked
    ):
        raise HTTPException(409, "Набор недоступен")
    db.refresh(v)
    if p.owner_id == user.id:
        raise HTTPException(409, "Вы уже автор этого проекта")
    filled = db.scalar(
        select(func.count())
        .select_from(Application)
        .where(Application.vacancy_id == v.id, Application.status == "accepted")
    )
    if filled >= v.capacity:
        raise HTTPException(409, "Все места на эту роль заняты")
    if db.scalar(
        select(Application)
        .join(Vacancy)
        .where(
            Vacancy.project_id == p.id,
            Application.user_id == user.id,
            Application.status == "accepted",
        )
    ):
        raise HTTPException(409, "Вы уже в команде проекта")
    previous = db.scalar(
        select(Application).where(
            Application.vacancy_id == v.id, Application.user_id == user.id
        )
    )
    if previous and previous.status not in ("withdrawn", "left"):
        raise HTTPException(409, "Отклик на эту роль уже отправлен")
    a = previous or Application(vacancy_id=v.id, user_id=user.id)
    a.message = data.message
    a.status = "pending"
    db.add(a)
    db.commit()
    return application_dict(db, a)


@router.get("/me/applications", response_model=list[ApplicationOut])
def my_applications(user=Depends(current_user), db: DB = Depends(get_db)):
    return [
        application_dict(db, a)
        for a in db.scalars(
            select(Application)
            .where(Application.user_id == user.id)
            .order_by(Application.id.desc())
        )
    ]


@router.get("/projects/{project_id}/applications", response_model=list[ApplicationOut])
def inbox(project_id: int, user=Depends(current_user), db: DB = Depends(get_db)):
    owner_only(get_project(db, project_id), user)
    return [
        application_dict(db, a)
        for a in db.scalars(
            select(Application)
            .join(Vacancy)
            .where(Vacancy.project_id == project_id)
            .order_by(Application.id.desc())
        )
    ]


@router.post("/applications/{application_id}/decision", response_model=ApplicationOut)
def decide(
    application_id: int,
    data: Decision,
    user=Depends(current_user),
    db: DB = Depends(get_db),
):
    a = db.get(Application, application_id)
    if not a:
        raise HTTPException(404, "Отклик не найден")
    v = db.get(Vacancy, a.vacancy_id)
    p = db.scalar(select(Project).where(Project.id == v.project_id).with_for_update())
    owner_only(p, user)
    db.refresh(v)
    db.refresh(
        a
    )  # another request may have decided it while waiting for the project lock
    if a.status != "pending":
        raise HTTPException(409, "Отклик уже рассмотрен")
    if p.status != "published" or not p.recruitment_open:
        raise HTTPException(409, "Набор закрыт или проект не опубликован")
    if db.get(User, a.user_id).is_blocked:
        raise HTTPException(409, "Аккаунт участника заблокирован")
    if data.status == "accepted":
        filled = db.scalar(
            select(func.count())
            .select_from(Application)
            .where(Application.vacancy_id == v.id, Application.status == "accepted")
        )
        if filled >= v.capacity:
            raise HTTPException(409, "Свободных мест больше нет")
        member = db.scalar(
            select(Application)
            .join(Vacancy)
            .where(
                Vacancy.project_id == p.id,
                Application.user_id == a.user_id,
                Application.status == "accepted",
            )
        )
        if member:
            raise HTTPException(409, "Участник уже в команде")
        # Other pending applications by this student in this project become rejected.
        others = db.scalars(
            select(Application)
            .join(Vacancy)
            .where(
                Vacancy.project_id == p.id,
                Application.user_id == a.user_id,
                Application.id != a.id,
                Application.status == "pending",
            )
        ).all()
        for other in others:
            other.status = "rejected"
    a.status = data.status
    db.commit()
    return application_dict(db, a)


@router.post("/applications/{application_id}/withdraw", response_model=ApplicationOut)
def withdraw(application_id: int, user=Depends(current_user), db: DB = Depends(get_db)):
    a = db.get(Application, application_id)
    if not a:
        raise HTTPException(404, "Отклик не найден")
    if a.user_id != user.id:
        raise HTTPException(403, "Это чужой отклик")
    v = db.get(Vacancy, a.vacancy_id)
    db.scalar(select(Project).where(Project.id == v.project_id).with_for_update())
    db.refresh(a)
    if a.status != "pending":
        raise HTTPException(409, "Можно отозвать только ожидающий отклик")
    a.status = "withdrawn"
    db.commit()
    return application_dict(db, a)


@router.delete("/projects/{project_id}/members/{user_id}", response_model=Message)
def remove_member(
    project_id: int, user_id: int, user=Depends(current_user), db: DB = Depends(get_db)
):
    p = db.scalar(select(Project).where(Project.id == project_id).with_for_update())
    if not p:
        raise HTTPException(404, "Проект не найден")
    if user.id != user_id and p.owner_id != user.id:
        raise HTTPException(403, "Недостаточно прав")
    if user_id == p.owner_id:
        raise HTTPException(409, "Автор не может покинуть свой проект")
    a = db.scalar(
        select(Application)
        .join(Vacancy)
        .where(
            Vacancy.project_id == p.id,
            Application.user_id == user_id,
            Application.status == "accepted",
        )
    )
    if not a:
        raise HTTPException(404, "Участник не найден")
    a.status = "left" if user.id == user_id else "removed"
    db.commit()
    return {
        "detail": (
            "Вы вышли из команды"
            if user.id == user_id
            else "Участник удалён из команды"
        )
    }

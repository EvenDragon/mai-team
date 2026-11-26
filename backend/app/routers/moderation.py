from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session as DB
from ..db import get_db
from ..models import User, Project
from ..schemas import Moderation, ProjectOut
from ..security import moderator
from ..services import project_dict, projects_dict, audit

router = APIRouter()


@router.get("/moderation/projects", response_model=list[ProjectOut])
def moderation_queue(user=Depends(moderator), db: DB = Depends(get_db)):
    return projects_dict(
        db,
        db.scalars(
            select(Project)
            .where(Project.status.in_(["pending", "hidden"]))
            .order_by(Project.id)
        ).all(),
        user,
    )


@router.post("/moderation/projects/{project_id}", response_model=ProjectOut)
def moderate(
    project_id: int, data: Moderation, user=Depends(moderator), db: DB = Depends(get_db)
):
    p = db.scalar(select(Project).where(Project.id == project_id).with_for_update())
    if not p:
        raise HTTPException(404, "Проект не найден")
    if p.owner_id == user.id:
        raise HTTPException(403, "Нельзя модерировать собственный проект")
    if p.status not in ("pending", "hidden"):
        raise HTTPException(409, "Проект уже рассмотрен")
    if data.status == "published" and db.get(User, p.owner_id).is_blocked:
        raise HTTPException(409, "Автор заблокирован")
    p.status = data.status
    p.moderation_note = data.note
    audit(db, user.id, data.status, data.note, project_id=p.id)
    db.commit()
    return project_dict(db, p, user)

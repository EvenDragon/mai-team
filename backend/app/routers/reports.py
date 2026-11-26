"""Reports are private to their author and moderators; reports never auto-hide content."""

import time
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, delete
from sqlalchemy.orm import Session as DB
from ..db import get_db
from ..models import User, Project, Session, Report, ModerationEvent
from ..schemas import ReportInput, ReportDecision, ReportOut, BlockInput, Message
from ..security import current_user, moderator
from ..services import get_project, is_member, audit

router = APIRouter()


def report_dict(db, r):
    target = db.get(Project, r.project_id) if r.project_id else db.get(User, r.user_id)
    return dict(
        id=r.id,
        target_type="project" if r.project_id else "user",
        target_id=r.project_id or r.user_id,
        target_name=target.title if r.project_id else target.name,
        reason=r.reason,
        message=r.message,
        status=r.status,
        resolution=r.resolution,
        created_at=r.created_at,
        resolved_at=r.resolved_at,
    )


@router.post("/reports", response_model=ReportOut, status_code=201)
def create_report(
    data: ReportInput, user=Depends(current_user), db: DB = Depends(get_db)
):
    # Serialize duplicate/report quota checks per reporter.
    db.scalar(select(User).where(User.id == user.id).with_for_update())
    project_id = data.target_id if data.target_type == "project" else None
    user_id = data.target_id if data.target_type == "user" else None
    if project_id:
        p = get_project(db, project_id)
        if p.owner_id == user.id:
            raise HTTPException(409, "Нельзя пожаловаться на свой проект")
        if (
            p.status != "published"
            and user.role != "moderator"
            and not is_member(db, p.id, user.id)
        ):
            raise HTTPException(404, "Проект не найден")
    else:
        target = db.get(User, user_id)
        if not target:
            raise HTTPException(404, "Профиль не найден")
        if user_id == user.id:
            raise HTTPException(409, "Нельзя пожаловаться на себя")
    pending = db.scalars(
        select(Report).where(Report.reporter_id == user.id, Report.status == "pending")
    ).all()
    if any(r.project_id == project_id and r.user_id == user_id for r in pending):
        raise HTTPException(409, "Ваша жалоба уже ожидает рассмотрения")
    if len(pending) >= 10:
        raise HTTPException(429, "Дождитесь рассмотрения предыдущих жалоб")
    r = Report(
        reporter_id=user.id,
        project_id=project_id,
        user_id=user_id,
        reason=data.reason,
        message=data.message,
        created_at=int(time.time()),
    )
    db.add(r)
    db.commit()
    return report_dict(db, r)


@router.get("/me/reports", response_model=list[ReportOut])
def my_reports(user=Depends(current_user), db: DB = Depends(get_db)):
    return [
        report_dict(db, r)
        for r in db.scalars(
            select(Report)
            .where(Report.reporter_id == user.id)
            .order_by(Report.id.desc())
        )
    ]


@router.get("/moderation/reports", response_model=list[ReportOut])
def report_queue(user=Depends(moderator), db: DB = Depends(get_db)):
    return [
        report_dict(db, r)
        for r in db.scalars(
            select(Report).where(Report.status == "pending").order_by(Report.id)
        )
    ]


def set_block(db, target, actor, blocked, note):
    if target.id == actor.id or target.role == "moderator":
        raise HTTPException(403, "Нельзя блокировать себя или другого модератора")
    target.is_blocked = blocked
    target.block_reason = note if blocked else ""
    if blocked:
        db.execute(delete(Session).where(Session.user_id == target.id))


@router.post("/moderation/reports/{report_id}", response_model=ReportOut)
def resolve_report(
    report_id: int,
    data: ReportDecision,
    user=Depends(moderator),
    db: DB = Depends(get_db),
):
    r = db.scalar(select(Report).where(Report.id == report_id).with_for_update())
    if not r:
        raise HTTPException(404, "Жалоба не найдена")
    if r.status != "pending":
        raise HTTPException(409, "Жалоба уже рассмотрена")
    p = (
        db.scalar(select(Project).where(Project.id == r.project_id).with_for_update())
        if r.project_id
        else None
    )
    target = db.scalar(
        select(User)
        .where(User.id == (p.owner_id if p else r.user_id))
        .with_for_update()
    )
    if target.id == user.id or r.reporter_id == user.id:
        raise HTTPException(
            403,
            "Собственную жалобу или жалобу на себя должен рассмотреть другой модератор",
        )
    if data.action == "hide":
        if not p:
            raise HTTPException(422, "Скрыть можно только проект")
        p.status = "hidden"
        p.moderation_note = data.note
    if data.action == "block":
        set_block(db, target, user, True, data.note)
    audit(
        db,
        user.id,
        data.action,
        data.note,
        project_id=r.project_id,
        user_id=target.id,
        report_id=r.id,
    )
    r.status = "resolved"
    r.resolution = data.note
    r.resolved_at = int(time.time())
    db.commit()
    return report_dict(db, r)


@router.get("/me/notices")
def notices(user=Depends(current_user), db: DB = Depends(get_db)):
    return [
        dict(
            id=e.id,
            action=e.action,
            note=e.note,
            created_at=e.created_at,
            project_id=e.project_id,
        )
        for e in db.scalars(
            select(ModerationEvent)
            .where(ModerationEvent.user_id == user.id)
            .order_by(ModerationEvent.id.desc())
            .limit(100)
        )
    ]


@router.get("/moderation/users")
def blocked_users(user=Depends(moderator), db: DB = Depends(get_db)):
    return [
        dict(id=u.id, name=u.name, reason=u.block_reason)
        for u in db.scalars(select(User).where(User.is_blocked == True))
    ]


@router.post("/moderation/users/{user_id}/block", response_model=Message)
def block_user(
    user_id: int, data: BlockInput, user=Depends(moderator), db: DB = Depends(get_db)
):
    target = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if not target:
        raise HTTPException(404, "Профиль не найден")
    set_block(db, target, user, data.blocked, data.note)
    audit(
        db,
        user.id,
        "block" if data.blocked else "unblock",
        data.note,
        user_id=target.id,
    )
    db.commit()
    return {
        "detail": "Аккаунт заблокирован" if data.blocked else "Аккаунт разблокирован"
    }


@router.get("/moderation/history")
def history(
    page: int = Query(1, ge=1), user=Depends(moderator), db: DB = Depends(get_db)
):
    return [
        dict(
            id=e.id,
            moderator_id=e.moderator_id,
            project_id=e.project_id,
            user_id=e.user_id,
            report_id=e.report_id,
            action=e.action,
            note=e.note,
            created_at=e.created_at,
        )
        for e in db.scalars(
            select(ModerationEvent)
            .order_by(ModerationEvent.id.desc())
            .offset((page - 1) * 50)
            .limit(50)
        )
    ]

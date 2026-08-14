"""时间胶囊路由：CRUD + 按 unlock_at 解锁判定（读取时自动破壳）"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.capsule import Capsule
from ..models.user import User
from .auth import get_current_user

router = APIRouter(prefix="/api/capsules", tags=["capsule"])


class CapsuleCreate(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    content: str = ""
    unlock_at: datetime  # ISO 时间；到点自动解锁


def _countdown(c: Capsule) -> str:
    """密封状态卡片的剩余天数描述（对齐 core.memory_manager.get_capsule_countdown）"""
    if c.unlocked:
        return ""
    days = (c.unlock_at.date() - datetime.now().date()).days
    if days <= 0:
        return "今天"
    if days == 1:
        return "明天"
    return f"还有 {days} 天"


def _to_api(c: Capsule) -> dict:
    return {
        "id": c.id,
        "title": c.title,
        "content": c.content,
        "unlock_at": c.unlock_at.isoformat(timespec="seconds"),
        "unlocked": c.unlocked,
        "countdown": _countdown(c),
        "created_at": c.created_at.isoformat(timespec="seconds"),
    }


@router.get("")
def list_capsules(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Capsule)
        .filter(Capsule.user_id == user.id)
        .order_by(Capsule.created_at)
        .all()
    )
    # 解锁判定：到点自动破壳并持久化
    now = datetime.now()
    changed = False
    for c in rows:
        if not c.unlocked and c.unlock_at <= now:
            c.unlocked = True
            changed = True
    if changed:
        db.commit()
    return {"capsules": [_to_api(c) for c in rows]}


@router.post("", status_code=201)
def create_capsule(
    req: CapsuleCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    c = Capsule(
        user_id=user.id,
        title=req.title.strip(),
        content=req.content,
        unlock_at=req.unlock_at,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return {"capsule": _to_api(c)}


@router.delete("/{capsule_id}")
def delete_capsule(
    capsule_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    c = (
        db.query(Capsule)
        .filter(Capsule.id == capsule_id, Capsule.user_id == user.id)
        .first()
    )
    if c is None:
        raise HTTPException(404, "胶囊不存在")
    db.delete(c)
    db.commit()
    return {"ok": True}

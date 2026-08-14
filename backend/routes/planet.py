"""星球路由：条目 CRUD + 生态/天气（复用 core.memory_manager）"""
from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core import memory_manager as mm

from ..database import get_db
from ..models.user import User
from ..services import planet_service
from .auth import get_current_user

router = APIRouter(prefix="/api/planet", tags=["planet"])


class EntryCreate(BaseModel):
    type: Literal["star", "cloud", "sprout", "story"]
    title: str = Field(min_length=1, max_length=128)
    content: str = ""
    mood: Optional[str] = None  # 心情云用：pink|blue|gray|yellow
    tags: list[str] = []


@router.get("/entries")
def list_entries(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = planet_service.list_entries(db, user.id)
    return {"entries": [planet_service.entry_to_api(r) for r in rows]}


@router.post("/entries", status_code=201)
def create_entry(
    req: EntryCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建条目（sprout 类型附带勇敢芽校验信息，校验失败仍保存）"""
    row, validation = planet_service.create_entry(
        db, user.id, req.type, req.title.strip(), req.content, req.mood, req.tags
    )
    return {"entry": planet_service.entry_to_api(row), "validation": validation}


@router.delete("/entries/{entry_id}")
def delete_entry(
    entry_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not planet_service.delete_entry(db, user.id, entry_id):
        raise HTTPException(404, "条目不存在")
    return {"ok": True}


@router.get("/weather")
def weather(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """星球天气：由近期心情云的 mood 分布推导（core.memory_manager）"""
    planet = planet_service.build_planet_dict(db, user.id)
    return mm.get_planet_weather(planet)


@router.get("/ecosystem")
def ecosystem(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """星球生态全景：天气 + 四类元素描述（core.memory_manager）"""
    planet = planet_service.build_planet_dict(db, user.id)
    return mm.get_planet_ecosystem(planet)

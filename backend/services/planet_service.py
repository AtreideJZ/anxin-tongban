"""星球服务：PlanetEntry 表 ⇄ core.memory_manager 的 legacy planet dict"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from core import memory_manager as mm

from ..models.planet import PlanetEntry

# planet dict 的 key 形状（与 data/planet.json、memory_manager._flatten_planet 对齐）
_PLURAL_KEYS = ("stars", "clouds", "sprouts", "stories")


def _cn_date(dt: datetime) -> str:
    """"7月1日" 中文日期格式（与 core/memory_manager.create_entry 一致）"""
    return dt.strftime("%m月%d日").lstrip("0")


def entry_to_legacy(row: PlanetEntry) -> dict:
    """DB 行 → memory_manager / pipeline 期望的条目 dict（legacy 前缀风格 id）"""
    d = {
        "id": f"{row.type[:2]}{row.id}",
        "type": row.type,
        "title": row.title,
        "content": row.content or "",
        "tags": row.tags or [],
        "source": row.source,
        "date": row.date,
    }
    if row.mood:
        d["mood"] = row.mood
    return d


def entry_to_api(row: PlanetEntry) -> dict:
    """DB 行 → API 响应 dict（id 用 DB 主键，供前端 CRUD）"""
    return {
        "id": row.id,
        "type": row.type,
        "title": row.title,
        "content": row.content or "",
        "mood": row.mood,
        "tags": row.tags or [],
        "source": row.source,
        "date": row.date,
        "created_at": row.created_at.isoformat(timespec="seconds"),
    }


def build_planet_dict(db: Session, user_id: int) -> dict:
    """从当前用户的 DB 条目组装 memory_manager 期望的 legacy planet dict"""
    rows = (
        db.query(PlanetEntry)
        .filter(PlanetEntry.user_id == user_id)
        .order_by(PlanetEntry.created_at)
        .all()
    )
    planet: dict = {k: [] for k in _PLURAL_KEYS}
    for row in rows:
        key = row.type + "s"
        if key in planet:
            planet[key].append(entry_to_legacy(row))
    return planet


def list_entries(db: Session, user_id: int) -> list[PlanetEntry]:
    return (
        db.query(PlanetEntry)
        .filter(PlanetEntry.user_id == user_id)
        .order_by(PlanetEntry.created_at.desc())
        .all()
    )


def create_entry(
    db: Session,
    user_id: int,
    entry_type: str,
    title: str,
    content: str = "",
    mood: Optional[str] = None,
    tags: Optional[list] = None,
    source: str = "manual",
) -> tuple[PlanetEntry, Optional[dict]]:
    """创建条目；sprout 类型走 core 的勇敢芽校验

    校验失败仍保存（不丢失孩子写的内容），校验信息随响应返回，
    由前端决定如何展示（与 core/memory_manager.create_entry 的设计一致）。
    """
    validation = None
    if entry_type == "sprout":
        validation = mm.validate_sprout_entry(title, content)
    now = datetime.now()
    row = PlanetEntry(
        user_id=user_id,
        type=entry_type,
        title=title,
        content=content,
        mood=mood,
        tags=list(tags or []),
        source=source,
        date=_cn_date(now),
        created_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row, validation


def delete_entry(db: Session, user_id: int, entry_id: int) -> bool:
    row = (
        db.query(PlanetEntry)
        .filter(PlanetEntry.id == entry_id, PlanetEntry.user_id == user_id)
        .first()
    )
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True

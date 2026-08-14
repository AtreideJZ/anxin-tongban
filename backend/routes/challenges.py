"""每日挑战路由（复用 core.daily_challenges）"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from core import daily_challenges

from ..models.user import User
from .auth import get_current_user

router = APIRouter(prefix="/api/challenges", tags=["challenges"])


@router.get("/today")
def today(user: User = Depends(get_current_user)):
    """今日挑战（按日期 hash 选取，同一天恒定）"""
    return {"challenge": daily_challenges.get_today_challenge()}

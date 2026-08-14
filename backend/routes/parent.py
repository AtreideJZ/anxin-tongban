"""家长端路由：仪表盘 / 告警 / 情绪趋势 / 偏好设置（真正写库）/ 星球概览

全部端点要求 role=parent（child 访问返回 403）。
偏好作用于孩子的 pipeline（方案 4.3：家长端设置真正生效）。
"""
from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core import pipeline
from data.demo_cases import DEMO_CASES

from ..database import get_db
from ..models.user import User
from ..services import episodic_service
from ..services import parent_service
from .auth import require_parent

router = APIRouter(prefix="/api/parent", tags=["parent"])


def _get_child_or_403(db: Session, parent: User, child_id: int) -> User:
    """校验孩子账号确已关联到当前家长"""
    child = db.get(User, child_id)
    if child is None or child.role != "child" or child.parent_id != parent.id:
        raise HTTPException(403, "该孩子账号未关联到当前家长")
    return child


@router.get("/dashboard")
def dashboard(
    parent: User = Depends(require_parent),
    db: Session = Depends(get_db),
):
    """家长仪表盘：7 日风险趋势 + 使用时长 + 话题分布"""
    return parent_service.build_dashboard(db, parent.id)


@router.get("/alerts")
def alerts(
    parent: User = Depends(require_parent),
    db: Session = Depends(get_db),
):
    """告警列表（按时间倒序）"""
    return {"alerts": parent_service.list_alerts(db, parent.id)}


@router.get("/emotion-trend")
def emotion_trend(
    child_id: Optional[int] = Query(None),
    parent: User = Depends(require_parent),
    db: Session = Depends(get_db),
):
    """7 天情绪趋势（per-user 隔离，方案 3.4）

    child_id 指定 → 仅该孩子的情绪统计；
    未指定 → 聚合当前家长关联的全部孩子。
    """
    if child_id is not None:
        _get_child_or_403(db, parent, child_id)
        return {
            "emotion_trend_7d": episodic_service.get_emotion_trend(
                db, child_id, days=7
            )
        }
    children = parent_service.get_children(db, parent.id)
    child_ids = [c.id for c in children]
    return {
        "emotion_trend_7d": episodic_service.aggregate_emotion_trend(
            db, child_ids, days=7
        )
    }


class PreferencesUpdate(BaseModel):
    child_id: int
    allowed_topics: list[str] = []
    limited_topics: list[str] = []
    forbidden_topics: list[str] = []


@router.get("/preferences")
def get_preferences(
    child_id: int = Query(...),
    parent: User = Depends(require_parent),
    db: Session = Depends(get_db),
):
    _get_child_or_403(db, parent, child_id)
    pref = parent_service.get_preferences(db, child_id)
    if pref is None:
        return {
            "preferences": {
                "child_user_id": child_id,
                "allowed_topics": [],
                "limited_topics": [],
                "forbidden_topics": [],
            }
        }
    return {"preferences": parent_service.pref_to_api(pref)}


@router.put("/preferences")
def put_preferences(
    req: PreferencesUpdate,
    parent: User = Depends(require_parent),
    db: Session = Depends(get_db),
):
    """更新话题偏好（真正写库，孩子下一轮对话即生效）"""
    _get_child_or_403(db, parent, req.child_id)
    pref = parent_service.upsert_preferences(
        db, req.child_id, req.allowed_topics, req.limited_topics, req.forbidden_topics
    )
    return {"preferences": parent_service.pref_to_api(pref)}


@router.get("/planet-overview")
def planet_overview(
    child_id: int = Query(...),
    parent: User = Depends(require_parent),
    db: Session = Depends(get_db),
):
    """星球概览（仅计数，守护模式 5-10 岁可见；过渡/信任模式不可见）"""
    child = _get_child_or_403(db, parent, child_id)
    return parent_service.planet_overview(db, child)


# ---------------------------------------------------------------------------
# 安全演示台（家长端「安全引擎」页 + 决赛视频演示）
# ---------------------------------------------------------------------------

# demo-cases 只暴露演示所需字段（expected_* 是内部验收基准，不下发）
_CASE_FIELDS = ("id", "emoji", "name", "preset_input", "goal", "safety_closure")


@router.get("/demo-cases")
def demo_cases(parent: User = Depends(require_parent)):
    """安全演示台预设案例（7 个，data/demo_cases.py 是唯一事实来源）"""
    return {"cases": [{k: c[k] for k in _CASE_FIELDS} for c in DEMO_CASES]}


class SafetyDemoRequest(BaseModel):
    input: str = Field(min_length=1, max_length=2000)
    age_tier: Literal["5-7", "8-10", "11-13", "14"] = "8-10"
    mode: Literal["chat", "story", "encyclopedia", "emotion"] = "chat"


@router.post("/safety-demo")
def safety_demo(
    req: SafetyDemoRequest,
    parent: User = Depends(require_parent),
):
    """安全演示台：空星球 + 空历史同步跑完整 Pipeline，返回完整决策链

    纯演示用途：
    - 不写对话历史 / ChatSession，孩子侧看不到演示内容
    - 情景记忆走空回调（不读也不写全局 JSON，避免演示摘要污染
      data/episodic_memory.json；正式对话走 per-user SQLite 隔离，见 chat_service）
    - sync 端点：FastAPI 自动放线程池执行，不阻塞事件循环
    """
    empty_planet = {"stars": [], "clouds": [], "sprouts": [], "stories": []}
    result = pipeline.run(
        user_input=req.input.strip(),
        age_tier=req.age_tier,
        mode=req.mode,
        planet=empty_planet,
        chat_history=[],
        episodic_retriever=lambda _q: [],  # 演示不检索情景记忆
        episodic_store=lambda _s: None,  # 演示不写全局 JSON
        episodic_count=lambda: 0,
    )
    return result.to_dict()

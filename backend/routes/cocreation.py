"""亲子共创路由（v2.2 拓展方向 B + C）

- POST /api/cocreation/topic：亲子话题卡（B）。AI 生成温暖话题，
  孩子拿着它去和父母面对面聊。不走 /api/chat/send，不计入使用时长。
- 共创故事（C，docs/v2.2-拓展方向.md 第五节）：
  - POST /api/cocreation/story/start      发起故事（AI 开头，留白）
  - POST /api/cocreation/story/turn       孩子/家长轮流接一段（孩子输入走完整 Pipeline）
  - POST /api/cocreation/story/finalize   完成润色（只改语法/错别字）+ 自动种小星球
  - GET  /api/cocreation/stories          孩子自己的故事列表
  - POST /api/cocreation/story/{id}/share 孩子主动分享给家长看
  - GET  /api/cocreation/family-stories   家长端：已分享的成品列表

设计纪律：
- story 端点仅孩子账号可用（家长发起共创返回 403）；family-stories 仅家长可用
- 共创全程不碰 usage_minutes（亲子活动，不是 AI 使用，方案 5.3）
"""
from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User
from ..services import cocreation_service
from .auth import get_current_user, require_parent

router = APIRouter(prefix="/api/cocreation", tags=["cocreation"])


@router.post("/topic")
def topic_card(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """亲子话题卡：生成一个年龄适配、已过滤敏感词的亲子话题

    设计约束（v2.2 拓展方向 4.2）：
    - 独立端点，不走 chat/send → 不触发 usage_minutes 计数
    - LLM 产出经关键词安全过滤，无 Key 时回退分龄预置话题库
    """
    return cocreation_service.generate_topic(user.age_tier or "")


# ---------------------------------------------------------------------------
# 共创故事（C）
# ---------------------------------------------------------------------------


class StoryStartRequest(BaseModel):
    title: Optional[str] = Field(default=None, max_length=64)


class StoryTurnRequest(BaseModel):
    story_id: int
    role: Literal["child", "parent"]  # 同设备轮流输入，由前端切换角色
    content: str = Field(min_length=1, max_length=500)


class StoryIdRequest(BaseModel):
    story_id: int


def _require_child(user: User = Depends(get_current_user)) -> User:
    """依赖：要求孩子角色（共创由孩子发起，家长账号发起返回 403）"""
    if user.role != "child":
        raise HTTPException(403, "共创故事是孩子发起的亲子活动，请用孩子账号开始哦")
    return user


@router.post("/story/start")
def story_start(
    req: StoryStartRequest,
    user: User = Depends(_require_child),
    db: Session = Depends(get_db),
):
    """发起共创故事：AI 生成开头（30-50 字、年龄适配、留白结尾）"""
    story = cocreation_service.start_story(db, user, req.title)
    opening = story.turns[0]["content"] if story.turns else ""
    return {"story": cocreation_service.story_to_dict(story), "opening": opening}


@router.post("/story/turn")
def story_turn(
    req: StoryTurnRequest,
    user: User = Depends(_require_child),
    db: Session = Depends(get_db),
):
    """接一段故事：孩子的输入先跑完整 Pipeline 审计，家长的输入做关键词检查

    accepted=false 时原文不入故事，ai_response 为安全回应（如危机模板）。
    """
    try:
        return cocreation_service.add_turn(
            db, user, req.story_id, req.role, req.content.strip()
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/story/finalize")
def story_finalize(
    req: StoryIdRequest,
    user: User = Depends(_require_child),
    db: Session = Depends(get_db),
):
    """完成润色：串联原文 → 只改语法/错别字 → 自动种小星球故事条目"""
    try:
        return cocreation_service.finalize_story(db, user, req.story_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/stories")
def story_list(
    user: User = Depends(_require_child),
    db: Session = Depends(get_db),
):
    """孩子自己的共创故事列表（时间倒序）"""
    rows = cocreation_service.list_stories(db, user)
    return {"stories": [cocreation_service.story_to_dict(s) for s in rows]}


@router.post("/story/{story_id}/share")
def story_share(
    story_id: int,
    user: User = Depends(_require_child),
    db: Session = Depends(get_db),
):
    """孩子主动把成品分享给家长看（成品默认孩子私密）"""
    try:
        story = cocreation_service.share_story(db, user, story_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"story": cocreation_service.story_to_dict(story)}


@router.get("/family-stories")
def family_stories(
    user: User = Depends(require_parent),
    db: Session = Depends(get_db),
):
    """家长端：关联孩子分享的成品共创故事（含孩子用户名）"""
    return {"stories": cocreation_service.list_shared_stories(db, user)}

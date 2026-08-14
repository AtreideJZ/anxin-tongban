"""对话路由：POST /api/chat/send（SSE 伪流式）+ GET /api/chat/history

SSE 事件序列（v2.1 方案 4.5，先审计、后伪流式）：
1. event: step  —— Pipeline 各步骤回放（驱动安全引擎决策链逐步点亮）
2. event: token —— 审计通过的 final_reply 按 3-4 字切块（打字机效果）
3. event: done  —— 结构化结果 + 推荐卡片 + 每日挑战 + 决策记录

【安全不变量（测试守着）】
- process_message 返回时 pipeline 已完整跑完，任何 token 都在审计之后流出
- critic_intercepted=True / 危机模板场景，流里只有替换后的安全文本
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core import pipeline

from ..database import get_db
from ..models.user import User
from ..services import chat_service
from .auth import get_current_user

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    # 方案 4.1：mode 已由 Pipeline Step 2 意图自动识别，此字段仅作为
    # 会话模式的兜底先验（首次对话无历史时用 "chat"），客户端不再手动选择。
    mode: str = "chat"


def _sse(event: str, data: dict) -> str:
    """手工格式化一条 SSE 消息（不加 sse-starlette 之类的新依赖）"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/send")
async def send(
    req: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    message = req.message.strip()
    if not message:
        raise HTTPException(400, "消息不能为空")

    # 此调用返回时 pipeline 已完整跑完（含双审与拦截替换），DB 也已持久化
    payload = await chat_service.process_message(db, user, message, req.mode)
    result: pipeline.PipelineResult = payload["result"]

    async def event_stream():
        # 1. step 事件：回放完整决策链，小延时营造逐步点亮效果
        for step in result.steps:
            yield _sse("step", asdict(step))
            await asyncio.sleep(0.05)
        # 2. token 事件：审计通过的 final_reply 按 3-4 字切块伪流式推送
        reply = result.final_reply
        for i in range(0, len(reply), 4):
            yield _sse("token", {"text": reply[i : i + 4]})
            await asyncio.sleep(0.03)
        # 3. done 事件：结构化结果 + 增强卡片
        yield _sse(
            "done",
            {
                "risk_level": result.risk_level,
                "topic": result.topic,
                "mode": result.mode,
                "strategy": result.strategy,
                "parent_alert": result.parent_alert,
                "used_crisis_template": result.used_crisis_template,
                "critic_intercepted": result.critic_intercepted,
                "recommendations": payload["recommendations"],
                "challenge": payload["challenge"],
                "decision_record": result.decision_record,
            },
        )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        # 防反向代理/浏览器缓冲导致伪流式失效
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/history")
def history(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """当前用户的会话消息"""
    session = chat_service.get_or_create_session(db, user.id)
    return {
        "messages": session.messages or [],
        "mode": session.mode,
        "usage_minutes": session.usage_minutes or 0,
    }

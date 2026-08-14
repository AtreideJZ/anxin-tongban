"""认证路由：注册（含监护人同意）/ 登录（JWT）/ 当前用户

- 注册：用户名 + 4 位 PIN + age_tier + role + 监护人同意必勾 + 可选 parent 关联
- 登录：PIN 校验 → JWT（pyjwt HS256，7 天过期）
- get_current_user 依赖：Authorization: Bearer <JWT>
"""
from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User
from ..services import user_service

router = APIRouter(prefix="/api/auth", tags=["auth"])
_bearer = HTTPBearer(auto_error=False)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=2, max_length=32)
    pin: str = Field(pattern=r"^\d{4}$")  # 4 位数字 PIN
    age_tier: Optional[Literal["5-7", "8-10", "11-13", "14"]] = None  # child 必填
    role: Literal["child", "parent"]
    guardian_consent: bool  # 监护人同意（合规，必勾，见方案 4.8）
    parent_username: Optional[str] = None  # 可选：关联已有家长账号


class LoginRequest(BaseModel):
    username: str
    pin: str


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """依赖：Authorization: Bearer <JWT> → 当前用户"""
    if credentials is None:
        raise HTTPException(401, "未登录")
    payload = user_service.decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(401, "登录已过期或无效")
    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise HTTPException(401, "用户不存在")
    return user


def require_parent(user: User = Depends(get_current_user)) -> User:
    """依赖：要求家长角色（child 访问返回 403）"""
    if user.role != "parent":
        raise HTTPException(403, "仅家长账号可访问")
    return user


@router.post("/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    # 监护人同意必勾（合规三件套，方案 4.8）
    if not req.guardian_consent:
        raise HTTPException(400, "注册必须勾选监护人同意")
    if req.role == "child" and not req.age_tier:
        raise HTTPException(400, "儿童账号必须选择年龄档位")
    if user_service.get_by_username(db, req.username):
        raise HTTPException(409, "用户名已存在")
    try:
        user = user_service.register(
            db,
            req.username,
            req.pin,
            req.age_tier,
            req.role,
            req.guardian_consent,
            req.parent_username,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {
        "token": user_service.create_token(user),
        "user": user_service.public_dict(user),
    }


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = user_service.authenticate(db, req.username, req.pin)
    if user is None:
        raise HTTPException(401, "用户名或 PIN 错误")
    return {
        "token": user_service.create_token(user),
        "user": user_service.public_dict(user),
    }


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"user": user_service.public_dict(user)}

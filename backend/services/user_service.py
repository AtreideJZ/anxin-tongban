"""用户服务：PIN 哈希、注册、登录、JWT 签发

- PIN 用 hashlib.pbkdf2_hmac 哈希（不引入 passlib）
- JWT 用 pyjwt HS256，密钥读 env JWT_SECRET（带开发默认值），7 天过期
"""
from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from sqlalchemy.orm import Session

from ..config import settings
from ..models.user import User

PBKDF2_ITERATIONS = 100_000
_JWT_ALGO = "HS256"


def hash_pin(pin: str) -> str:
    """PIN → "salt_hex:hash_hex" 存储格式"""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"{salt.hex()}:{digest.hex()}"


def verify_pin(pin: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split(":")
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256", pin.encode("utf-8"), bytes.fromhex(salt_hex), PBKDF2_ITERATIONS
    )
    return hmac.compare_digest(digest.hex(), digest_hex)


def create_token(user: User) -> str:
    """签发 JWT（HS256，7 天过期）"""
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "exp": datetime.now(timezone.utc) + timedelta(days=settings.jwt_expire_days),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_JWT_ALGO)


def decode_token(token: str) -> Optional[dict]:
    """解析 JWT，无效/过期返回 None"""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[_JWT_ALGO])
    except jwt.PyJWTError:
        return None


def get_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()


def register(
    db: Session,
    username: str,
    pin: str,
    age_tier: Optional[str],
    role: str,
    guardian_consent: bool,
    parent_username: Optional[str] = None,
) -> User:
    """注册新用户；child 可选关联已存在的家长账号"""
    parent_id = None
    if parent_username:
        parent = get_by_username(db, parent_username)
        if parent is None or parent.role != "parent":
            raise ValueError("关联的家长账号不存在")
        parent_id = parent.id
    user = User(
        username=username,
        pin_hash=hash_pin(pin),
        age_tier=age_tier if role == "child" else None,
        role=role,
        guardian_consent=guardian_consent,
        parent_id=parent_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, username: str, pin: str) -> Optional[User]:
    user = get_by_username(db, username)
    if user is None or not verify_pin(pin, user.pin_hash):
        return None
    return user


def public_dict(user: User) -> dict:
    """脱敏的用户信息（供 API 响应）"""
    return {
        "id": user.id,
        "username": user.username,
        "age_tier": user.age_tier,
        "role": user.role,
        "parent_id": user.parent_id,
        "guardian_consent": user.guardian_consent,
    }

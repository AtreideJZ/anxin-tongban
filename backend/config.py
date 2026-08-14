"""后端配置（pydantic-settings）

配置只走环境变量 / 项目根 .env 文件（v2.1 起不再读 st.secrets）。
环境变量统一前缀 ANXIN_；JWT_SECRET 兼容无前缀写法（部署平台常用）。
"""
from __future__ import annotations

from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录（backend/ 的上一级）
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ANXIN_",
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # SQLite 库文件：data/anxin.db（见 v2.1 方案 2.3）
    database_url: str = f"sqlite:///{(PROJECT_ROOT / 'data' / 'anxin.db').as_posix()}"

    # JWT 签名密钥：读 env JWT_SECRET（或 ANXIN_JWT_SECRET），带开发默认值
    jwt_secret: str = Field(
        default="anxin-dev-secret-do-not-use-in-prod!!",
        validation_alias=AliasChoices("JWT_SECRET", "ANXIN_JWT_SECRET"),
    )
    jwt_expire_days: int = 7

    # 情景记忆 JSON 存储路径（safety-demo 演示路径使用；正式对话走 per-user SQLite，
    # 见 backend/services/episodic_service.py）
    episodic_store: str = str(PROJECT_ROOT / "data" / "episodic_memory.json")

    # CORS 允许来源（逗号分隔）：默认仅 Vite 开发服务器；
    # 生产单进程同源托管前端产物，无需跨域。前后端分离部署时用 ANXIN_CORS_ORIGINS 覆盖
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"


settings = Settings()

# JWT 开发默认密钥（与 Settings 默认值一致）；生产环境必须经 env 覆盖
_DEV_JWT_SECRET = "anxin-dev-secret-do-not-use-in-prod!!"


def jwt_using_default_secret() -> bool:
    """当前 JWT 密钥是否为公开的开发默认值（生产部署必须修改）"""
    return settings.jwt_secret == _DEV_JWT_SECRET

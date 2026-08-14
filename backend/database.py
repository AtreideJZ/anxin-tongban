"""SQLAlchemy 引擎与会话管理（SQLite，库文件 data/anxin.db）"""
from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

# check_same_thread=False：SSE/线程池场景下 SQLite 允许多线程访问
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _conn_rec):
    """WAL 模式 + 忙等待：避免多用户同时对话时线程池写入报 database is locked"""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """全部 ORM 模型的基类"""


def get_db():
    """FastAPI 依赖：每请求一个 DB 会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """建表（幂等）。导入 models 确保全部模型已注册到 metadata。"""
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_age_tiers()


def _migrate_age_tiers() -> None:
    """v2.2 旧档位数据迁移（docs/v2.2-拓展方向.md 3.3）

    存量 users / episodic_memories 的旧档位值直接映射：
    "8-11" → "8-10"，"12-14" → "11-13"（保守，不自动升到 14 档）。
    幂等：重复执行无副作用。
    """
    from sqlalchemy import text

    from core.age_tiers import LEGACY_AGE_TIER_MAP

    with engine.begin() as conn:
        for table in ("users", "episodic_memories"):
            for old, new in LEGACY_AGE_TIER_MAP.items():
                conn.execute(
                    text(f"UPDATE {table} SET age_tier = :new WHERE age_tier = :old"),
                    {"new": new, "old": old},
                )

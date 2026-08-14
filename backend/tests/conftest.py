"""pytest 配置：临时 SQLite + 强制无 LLM（fallback 模式）+ 情景记忆内存存储

关键：环境覆盖必须在 import backend.* 之前完成（backend.config 在导入时读取 env）。
"""
import json
import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 临时 SQLite 库（测试不碰 data/anxin.db）
_TMP_DIR = tempfile.mkdtemp(prefix="anxin_test_")
os.environ["ANXIN_DATABASE_URL"] = f"sqlite:///{Path(_TMP_DIR, 'test.db').as_posix()}"

# 无 LLM API Key 也必须全绿：强制 fallback 模式
for _k in ("DEEPSEEK_API_KEY", "SILICONFLOW_API_KEY"):
    os.environ.pop(_k, None)

# 情景记忆用内存存储（测试不碰 data/episodic_memory.json）
import core.episodic_memory as em  # noqa: E402

em.init_store(":memory:")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.database import Base, engine  # noqa: E402
from backend.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_db():
    """每个测试函数一个干净的库"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# 测试辅助函数
# ---------------------------------------------------------------------------
def register_and_login(
    client,
    username: str,
    pin: str = "1234",
    age_tier: str | None = "8-10",
    role: str = "child",
    parent_username: str | None = None,
) -> str:
    """注册并返回 JWT token"""
    body = {
        "username": username,
        "pin": pin,
        "age_tier": age_tier,
        "role": role,
        "guardian_consent": True,
    }
    if parent_username:
        body["parent_username"] = parent_username
    r = client.post("/api/auth/register", json=body)
    assert r.status_code == 200, r.text
    return r.json()["token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def parse_sse(text: str) -> list[tuple[str, dict]]:
    """解析 SSE 文本 → [(event, data_dict), ...]"""
    events = []
    for block in text.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        event, data = None, None
        for line in block.splitlines():
            if line.startswith("event:"):
                event = line[len("event:") :].strip()
            elif line.startswith("data:"):
                data = line[len("data:") :].strip()
        if event:
            events.append((event, json.loads(data) if data else None))
    return events


def send_chat(client, token: str, message: str, mode: str = "chat"):
    """发送一条消息并读完整个 SSE 流，返回 [(event, data), ...]"""
    r = client.post(
        "/api/chat/send",
        json={"message": message, "mode": mode},
        headers=auth_headers(token),
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/event-stream")
    return parse_sse(r.text)

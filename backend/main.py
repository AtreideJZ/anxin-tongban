"""FastAPI 入口（v2.1 全栈重构后端）

启动方式（从项目根运行）：
    uvicorn backend.main:app --reload

说明：
- 顶部把项目根加入 sys.path，使 `import core.xxx`（安全引擎）可用
- 情景记忆沿用 core.episodic_memory 的 JSON 机制（pipeline 内部自动调用）
- 前端 vite build 产物存在时由本进程直接托管（单进程部署，方案 2.2）
"""
from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

# 把项目根加入 sys.path，使 `import core.xxx` 可用（安全引擎复用）
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.database import init_db
from backend.routes import auth, capsule, challenges, chat, cocreation, parent, planet


@asynccontextmanager
async def lifespan(app: FastAPI):
    import logging

    from backend.config import jwt_using_default_secret

    if jwt_using_default_secret():
        logging.getLogger("backend").warning(
            "JWT_SECRET 未设置，正在使用开发默认密钥——生产部署请务必修改"
        )

    init_db()
    # 情景记忆说明：正式对话走 per-user SQLite 隔离（chat_service 经 episodic_* 回调）；
    # safety-demo 演示路径传空回调（不读不写）；全局 JSON 仅 Streamlit 旧版使用。
    import core.episodic_memory as em

    if em._store_path is None:  # 测试环境可能已初始化为 ":memory:"
        em.init_store(settings.episodic_store)
    yield


app = FastAPI(title="安心童伴 API", version="2.1.0", lifespan=lifespan)

# CORS 显式白名单（默认仅 Vite 开发源；生产单进程同源托管前端产物，无跨域问题。
# 前后端分离部署时通过 ANXIN_CORS_ORIGINS 环境变量配置正式域名）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (auth, chat, planet, capsule, challenges, parent, cocreation):
    app.include_router(module.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# 托管前端构建产物（frontend/dist 存在时；放最后，避免覆盖 /api 路由）
# SPA 回退：非 /api 路径一律返回 index.html，直接刷新 /chat 等前端路由不 404
_dist = PROJECT_ROOT / "frontend" / "dist"
if _dist.exists():
    from fastapi.responses import FileResponse, JSONResponse

    if (_dist / "assets").exists():
        app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        candidate = _dist / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_dist / "index.html")

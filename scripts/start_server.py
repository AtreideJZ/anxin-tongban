"""安心童伴 v2.1 生产一键启动脚本

用途：国内轻量云服务器 / 本地生产模式部署（单进程托管 API + 前端产物）。

步骤：
    1. 建库 + 生成演示账号（幂等，已存在则跳过）
    2. 启动 uvicorn（FastAPI 托管 frontend/dist）

用法（从项目根运行）：
    python scripts/start_server.py                 # 默认 0.0.0.0:8765
    python scripts/start_server.py --port 8000
    python scripts/start_server.py --no-seed        # 跳过演示账号种子

依赖 .env（见 .env.example）；无 LLM Key 也可运行
（脚本回退模式，安全闭环完整，只是不展示真实 LLM 生成）。
"""
from __future__ import annotations

import argparse
import sys
import threading
import webbrowser
from pathlib import Path

# Windows GBK 控制台无法打印 ⚠️ 等字符，启动前统一 stdout/stderr 为 UTF-8
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass  # 极端环境下退化为默认编码，不影响启动

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="安心童伴 v2.1 生产启动")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址（默认 0.0.0.0）")
    parser.add_argument("--port", type=int, default=8765, help="监听端口（默认 8765）")
    parser.add_argument("--no-seed", action="store_true", help="跳过演示账号种子")
    parser.add_argument("--open", action="store_true", help="启动后自动打开浏览器")
    args = parser.parse_args()

    # 1. 建库 + 演示账号种子（幂等）
    if not args.no_seed:
        from backend.database import SessionLocal, init_db
        from backend.seed import run_seed

        init_db()
        db = SessionLocal()
        try:
            run_seed(db)
        finally:
            db.close()
    else:
        from backend.database import init_db

        init_db()

    # 生产安全提醒：JWT 密钥仍为公开默认值时给出醒目警告（部署务必设置 JWT_SECRET）
    from backend.config import jwt_using_default_secret

    if jwt_using_default_secret():
        print("\n⚠️  警告：JWT_SECRET 未设置，正在使用公开的开发默认密钥！")
        print("   生产环境存在伪造登录风险，请在 .env 中设置强随机 JWT_SECRET。\n")

    # 2. 启动 uvicorn
    import uvicorn

    if args.open:
        def _open_browser() -> None:
            webbrowser.open(f"http://localhost:{args.port}")
        threading.Timer(1.5, _open_browser).start()

    print(f"\n安心童伴已启动：http://localhost:{args.port}")
    print("   演示账号：demo_kid (PIN 1234) | demo_parent (PIN 0000)\n")
    uvicorn.run("backend.main:app", host=args.host, port=args.port, workers=1)


if __name__ == "__main__":
    main()

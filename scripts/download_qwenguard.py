"""下载 Qwen3Guard-Gen-0.6B GGUF 模型（~400MB）

安心童伴的 Step 1b/6c 安全分类依赖本地 Qwen3Guard 模型。
模型文件较大（~400MB）不入 git 库，首次运行前用本脚本下载。

用法：
    python scripts/download_qwenguard.py

下载源（按优先级自动尝试）：
    1. hf-mirror.com（国内可访问的 HuggingFace 镜像）
    2. huggingface.co（官方源，需网络可达）

模型文件：QuantFactory/Qwen3Guard-Gen-0.6B-GGUF · Q4_K_M 量化版
保存位置：models/qwen3guard-gen-0.6b.Q4_K_M.gguf（core/qwen_guard.py 默认搜索路径）

说明：官方仓库 Qwen/Qwen3Guard-Gen-0.6B-GGUF 在 HuggingFace 上需要登录授权，
QuantFactory 的量化镜像内容相同且公开可下。如需其他量化规格（Q8_0 等），
可设置环境变量 QWENGUARD_MODEL_PATH 指向自定义路径。
"""
from __future__ import annotations

import os
import sys
import urllib.request

MODEL_NAME = "Qwen3Guard-Gen-0.6B.Q4_K_M.gguf"
DEST = os.path.join(
    os.path.dirname(__file__), "..", "models", "qwen3guard-gen-0.6b.Q4_K_M.gguf"
)

SOURCES = [
    f"https://hf-mirror.com/QuantFactory/Qwen3Guard-Gen-0.6B-GGUF/resolve/main/{MODEL_NAME}",
    f"https://huggingface.co/QuantFactory/Qwen3Guard-Gen-0.6B-GGUF/resolve/main/{MODEL_NAME}",
]


def _progress(block_num: int, block_size: int, total_size: int) -> None:
    downloaded = block_num * block_size
    if total_size > 0:
        pct = min(100, downloaded * 100 / total_size)
        mb = downloaded / 1024 / 1024
        total_mb = total_size / 1024 / 1024
        print(f"\r  {mb:.0f}/{total_mb:.0f} MB ({pct:.1f}%)", end="", flush=True)


def download() -> bool:
    dest = os.path.abspath(DEST)
    os.makedirs(os.path.dirname(dest), exist_ok=True)

    if os.path.exists(dest):
        size_mb = os.path.getsize(dest) / 1024 / 1024
        if size_mb > 300:  # 已存在且大小合理 → 视为已下载
            print(f"模型已存在：{dest}（{size_mb:.0f} MB），跳过下载")
            return True
        print(f"发现不完整文件（{size_mb:.0f} MB），重新下载")
        os.remove(dest)

    for url in SOURCES:
        print(f"尝试下载源：{url}")
        try:
            urllib.request.urlretrieve(url, dest, _progress)
            print()  # 换行
            size_mb = os.path.getsize(dest) / 1024 / 1024
            if size_mb < 300:
                print(f"下载文件异常（仅 {size_mb:.0f} MB），尝试下一个源")
                os.remove(dest)
                continue
            print(f"下载完成：{dest}（{size_mb:.0f} MB）")
            return True
        except Exception as e:
            print(f"\n该源下载失败：{e}")

    print("所有下载源均失败。可手动下载后放到 models/ 目录，")
    print("或设置环境变量 QWENGUARD_MODEL_PATH 指向模型文件。")
    print("提示：没有模型文件时，安全引擎会自动降级（Step 1b/6c 跳过），不影响运行。")
    return False


if __name__ == "__main__":
    sys.exit(0 if download() else 1)

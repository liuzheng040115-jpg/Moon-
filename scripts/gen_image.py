r"""命令行生图：把提示词发给中转站的 gpt-image 系列模型，落一张图到本地。

用法：
    python gen_image.py "一只蓝色的鲸鱼娘在喝咖啡" -o E:\qqbot\.tmp\out.png
    python gen_image.py "..." --model gpt-image-2.5 --size 1024x1024 --n 1

凭证来源（按顺序）：
    1. 环境变量 GPT_API_KEY
    2. ~/.dsh/.credentials.yaml 里的 refs.GPT_API_KEY
    3. qqbot 的 .env 里的 GPT_API_KEY

只有 OpenAI 系的 gpt-image，审查比较严；提示词里的露骨内容会被直接拒。
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

DEFAULT_BASE = "https://heilovehei.com/v1"
# 实测：gpt-image-2 对稍微擦边的描述直接 451 拒；2.5 系列宽松得多，同一段提示词能出图。
DEFAULT_MODEL = "gpt-image-2.5"


def _read_credentials_yaml(path: Path) -> str | None:
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("GPT_API_KEY:"):
            return stripped.split(":", 1)[1].strip()
    return None


def _read_dotenv(path: Path) -> str | None:
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("GPT_API_KEY="):
            return stripped.split("=", 1)[1].strip()
    return None


def resolve_key() -> tuple[str, str]:
    """返回 (key, 来源说明)。"""
    env = os.environ.get("GPT_API_KEY", "").strip()
    if env:
        return env, "环境变量"

    for candidate, label in (
        (Path.home() / ".dsh" / ".credentials.yaml", "DSH 凭证"),
        (Path(__file__).resolve().parents[1] / ".env", ".env"),
    ):
        found = (
            _read_credentials_yaml(candidate)
            if candidate.suffix == ".yaml"
            else _read_dotenv(candidate)
        )
        if found:
            return found, label

    raise SystemExit("找不到 GPT_API_KEY：设环境变量，或写进 ~/.dsh/.credentials.yaml / .env")


def generate(
    prompt: str,
    model: str,
    size: str,
    base: str,
    key: str,
    timeout: int = 300,
) -> dict:
    payload = {"model": model, "prompt": prompt, "n": 1, "size": size}
    req = urllib.request.Request(
        base.rstrip("/") + "/images/generations",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise SystemExit(f"接口返回 HTTP {exc.code}：{detail[:600]}") from exc


def save_result(body: dict, out: Path) -> Path:
    item = (body.get("data") or [{}])[0]
    out.parent.mkdir(parents=True, exist_ok=True)

    if item.get("b64_json"):
        out.write_bytes(base64.b64decode(item["b64_json"]))
        return out

    url = item.get("url")
    if not url:
        raise SystemExit(f"返回里没有图片数据：{json.dumps(body)[:400]}")

    with urllib.request.urlopen(url, timeout=120) as resp:
        out.write_bytes(resp.read())
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="用 gpt-image 系列模型生成一张图")
    parser.add_argument("prompt", help="提示词")
    parser.add_argument("-o", "--out", default=None, help="输出文件路径")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"模型名，默认 {DEFAULT_MODEL}")
    parser.add_argument("--size", default="1024x1024", help="尺寸，如 1024x1024 / 1536x1024")
    parser.add_argument("--base", default=DEFAULT_BASE, help="接口 baseURL")
    parser.add_argument("--timeout", type=int, default=300, help="请求超时秒数")
    args = parser.parse_args()

    key, source = resolve_key()
    out = Path(args.out) if args.out else Path(__file__).resolve().parents[1] / ".tmp" / "gen.png"

    print(f"模型 {args.model} / 尺寸 {args.size} / key 来自{source}")
    print(f"提示词：{args.prompt}")
    body = generate(args.prompt, args.model, args.size, args.base, key, args.timeout)
    path = save_result(body, out)
    print(f"已保存：{path}（{path.stat().st_size} 字节）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

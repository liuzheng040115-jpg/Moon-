"""两层记录：全局日记 + 每个人的档案。

- 全局日记：data/diary/YYYY-MM-DD.md，一天一篇，散文，按日期存。
  记什么由她自己挑，不记流水账，只记她感兴趣、会被触动的。
- 人物档案：data/people/<QQ>.md，每个聊过的人一份，
  记这个人的脾性、喜好、相处感觉、最近在忙什么。

提示词里优先给最近的日记、再给当前这个人的档案。
日记可以长，但塞进提示词时只取开头，避免把上下文撑爆。
"""

from __future__ import annotations

import os
import re
import threading
import time
from datetime import date, datetime, timedelta
from pathlib import Path

# 日记同一天最多追加多少段
MAX_DIARY_ENTRIES = 8
# 单段日记最多多少字（用户说不限，这里只防住失控）
MAX_DIARY_ENTRY_CHARS = 1200
# 人物档案最多保留多少条
MAX_PROFILE_LINES = 40
# 塞进提示词时的截断长度
DIARY_PROMPT_CHARS = 700
PROFILE_PROMPT_CHARS = 900
# 提示词里带最近几天的日记
DIARY_DAYS_IN_PROMPT = 3


def _safe_id(user_id: str | int) -> str:
    text = re.sub(r"[^0-9A-Za-z_-]", "", str(user_id))[:32]
    return text or "unknown"


class Diaries:
    """全局日记目录 data/diary/。"""

    def __init__(self, root: str | Path = "data/diary") -> None:
        self.root = Path(root)
        self._lock = threading.RLock()
        if str(root) != ":memory:":
            self.root.mkdir(parents=True, exist_ok=True)

    def _path_for(self, day: date | None = None) -> Path:
        day = day or datetime.now().date()
        return self.root / f"{day.isoformat()}.md"

    def write(self, text: str, day: date | None = None) -> bool:
        """往今天的日记里追加一段。返回是否真的写了。"""
        body = (text or "").strip()
        if not body:
            return False
        if len(body) > MAX_DIARY_ENTRY_CHARS:
            body = body[:MAX_DIARY_ENTRY_CHARS]

        path = self._path_for(day)
        with self._lock:
            existing = ""
            try:
                existing = path.read_text(encoding="utf-8")
            except OSError:
                existing = ""

            blocks = [b for b in existing.split("\n\n---\n\n") if b.strip()]
            # 去掉文件头，只留正文
            if blocks and blocks[0].startswith("# "):
                blocks = blocks[1:]
            if any(body == b.strip() for b in blocks):
                return False
            blocks.append(body)
            blocks = blocks[-MAX_DIARY_ENTRIES:]

            stamp = (day or datetime.now().date()).isoformat()
            header = f"# {stamp}\n\n<!-- 最后更新：{time.strftime('%H:%M')} -->\n\n"
            content = header + "\n\n---\n\n".join(blocks) + "\n"
            try:
                tmp = path.with_suffix(".md.tmp")
                tmp.write_text(content, encoding="utf-8")
                os.replace(tmp, path)
                return True
            except OSError:
                return False

    def recent_days(self, count: int = DIARY_DAYS_IN_PROMPT) -> list[tuple[str, str]]:
        """返回最近几天 [(日期, 正文)]，新的在后。"""
        files = sorted(
            (p for p in self.root.glob("*.md") if re.fullmatch(r"\d{4}-\d{2}-\d{2}\.md", p.name)),
            reverse=True,
        )[: max(1, count)]
        out: list[tuple[str, str]] = []
        for path in reversed(files):
            try:
                raw = path.read_text(encoding="utf-8")
            except OSError:
                continue
            body = self._body_of(raw)
            if body:
                out.append((path.stem, body))
        return out

    @staticmethod
    def _body_of(raw: str) -> str:
        """去掉文件头和注释，留下正文（多段用空行接起来）。"""
        blocks: list[str] = []
        for chunk in raw.split("\n\n---\n\n"):
            lines = [
                line
                for line in chunk.splitlines()
                if not line.startswith("# ") and not line.strip().startswith("<!--")
            ]
            text = "\n".join(lines).strip()
            if text:
                blocks.append(text)
        return "\n\n".join(blocks)

    def prompt_fragment(self, count: int = DIARY_DAYS_IN_PROMPT) -> str:
        days = self.recent_days(count)
        if not days:
            return ""
        lines: list[str] = []
        for stamp, body in days:
            snippet = body if len(body) <= DIARY_PROMPT_CHARS else body[:DIARY_PROMPT_CHARS] + "……"
            lines.append(f"{stamp}　{snippet}")
        return (
            "\n\n你自己这些天写的日记（是你写的，不是谁给你的资料；"
            "当作你正过着的日子，接着往下过，别复述）：\n"
            + "\n\n".join(lines)
            + "\n"
        )

    def today_written(self) -> bool:
        return self._path_for().exists()


class People:
    """人物档案目录 data/people/。"""

    def __init__(self, root: str | Path = "data/people") -> None:
        self.root = Path(root)
        self._lock = threading.RLock()
        if str(root) != ":memory:":
            self.root.mkdir(parents=True, exist_ok=True)

    def _path_for(self, user_id: str | int) -> Path:
        return self.root / f"{_safe_id(user_id)}.md"

    def remember(self, user_id: str | int, text: str, name: str = "") -> bool:
        """给某个人记一条。重复的不写。"""
        body = " ".join((text or "").split())
        if not body:
            return False
        if len(body) > 200:
            body = body[:200]

        path = self._path_for(user_id)
        with self._lock:
            try:
                raw = path.read_text(encoding="utf-8")
            except OSError:
                raw = ""

            lines: list[str] = []
            display = name or str(user_id)
            for line in raw.splitlines():
                stripped = line.strip()
                if stripped.startswith("# "):
                    display = stripped[2:].strip() or display
                elif stripped.startswith("- "):
                    lines.append(stripped[2:].strip())
            if body in lines:
                return False
            lines.append(body)
            lines = lines[-MAX_PROFILE_LINES:]

            content = (
                f"# {display}\n\n"
                f"<!-- 最后更新：{time.strftime('%Y-%m-%d %H:%M')} -->\n\n"
                + "\n".join(f"- {item}" for item in lines)
                + "\n"
            )
            try:
                tmp = path.with_suffix(".md.tmp")
                tmp.write_text(content, encoding="utf-8")
                os.replace(tmp, path)
                return True
            except OSError:
                return False

    def entries(self, user_id: str | int) -> list[str]:
        path = self._path_for(user_id)
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            return []
        return [line[2:].strip() for line in raw.splitlines() if line.startswith("- ")]

    def prompt_fragment(self, user_id: str | int, name: str = "") -> str:
        items = self.entries(user_id)
        if not items:
            return ""
        body = "\n".join(f"- {item}" for item in items)
        if len(body) > PROFILE_PROMPT_CHARS:
            body = body[:PROFILE_PROMPT_CHARS] + "\n……"
        who = name or str(user_id)
        return (
            f"\n\n你记着的关于「{who}」的事（你自己攒下来的印象，别逐条念出来）：\n"
            + body
            + "\n"
        )

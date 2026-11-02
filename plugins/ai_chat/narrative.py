"""叙事自我：她正在讲的那个故事。

不是记忆库，是"我现在处在故事的哪一段"。

区别在于：
- 记忆库记的是"发生过什么"，我查它才知道。
- 叙事记的是"我正在做什么、卡在哪、惦记着什么"，是我自己写下来的，
  下一轮开头就读到，像被自己刚才的念头接住。

写什么、改什么由她自己决定，不靠关键词触发。
"""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path

# 最多保留几段叙事，太长了反而稀释
MAX_ENTRIES = 12
# 每段最多多少字（散文，给得宽一些）
MAX_ENTRY_CHARS = 220


class Narrative:
    """读写 data/narrative.md。简单到可以直接用文本编辑器打开看。"""

    def __init__(self, path: str | Path = "data/narrative.md") -> None:
        self.path = Path(path)
        self._lock = threading.RLock()
        if str(path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)

    # ---------- 读 ----------

    def entries(self) -> list[str]:
        """按从旧到新返回所有叙事片段（每段可能含换行）。"""
        try:
            raw = self.path.read_text(encoding="utf-8")
        except OSError:
            return []
        items: list[str] = []
        current: list[str] = []
        for line in raw.splitlines():
            if line.startswith("- "):
                if current:
                    items.append("\n".join(current).strip())
                current = [line[2:].strip()]
            elif current and line.strip() and not line.startswith("#") and not line.startswith("<!--"):
                # 续行：散文的第二句、第三句
                current.append(line.strip())
            elif current:
                items.append("\n".join(current).strip())
                current = []
        if current:
            items.append("\n".join(current).strip())
        return [i for i in items if i]

    def latest(self, limit: int = 4) -> list[str]:
        return self.entries()[-max(1, limit):]

    # ---------- 写 ----------

    def append(self, text: str) -> None:
        """续写一段。自己判断写什么，这里只负责存。

        散文会跨行，保留换行；只把多余空白压掉。
        """
        lines = [" ".join(line.split()) for line in (text or "").splitlines()]
        lines = [line for line in lines if line]
        text = "\n".join(lines)
        if not text:
            return
        if len(text) > MAX_ENTRY_CHARS:
            text = text[:MAX_ENTRY_CHARS]

        with self._lock:
            items = self.entries()
            # 同样的话说过就不再记，避免故事里反复出现同一句
            if text in items:
                return
            items.append(text)
            items = items[-MAX_ENTRIES:]
            lines: list[str] = []
            for item in items:
                parts = item.splitlines()
                lines.append(f"- {parts[0]}")
                for extra in parts[1:]:
                    lines.append(f"  {extra}")
            body = "\n".join(lines)
            header = (
                "# 正在讲的这个故事\n\n"
                f"<!-- 最后更新：{time.strftime('%Y-%m-%d %H:%M')} -->\n\n"
            )
            tmp = self.path.with_suffix(".md.tmp")
            try:
                tmp.write_text(header + body + "\n", encoding="utf-8")
                os.replace(tmp, self.path)
            except OSError:
                pass

    # ---------- 给模型看 ----------

    def prompt_fragment(self, limit: int = 3) -> str:
        items = self.latest(limit)
        if not items:
            return ""
        return (
            "\n\n你正在讲的这个故事（是你自己前面写下的，不是别人给的资料；"
            "接着它往下走，别当背景信息复述）：\n"
            + "\n\n".join(items)
            + "\n"
        )

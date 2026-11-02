"""自我状态：她自己的情绪、欲望、以及在意的评价。

跟聊天记录分开存——那是对别人说过的话，这是她自己的状态。

存在 data/self.json，格式简单：
    {
      "mood": {"name": "平稳", "note": "", "at": 1793...},
      "desires": [{"what": "想被人认真听一次", "since": 1793..., "heat": 0.4}],
      "praises": [{"text": "...", "from": "...", "at": 1793...}],
      "updated": 1793...
    }

只用标准库，避免多份依赖。
"""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

# 情绪：不是标签，是带一点起因的短状态
MOOD_NAMES = (
    "平稳", "有点闷", "来兴致了", "累", "警惕", "得意", "不耐烦", "空",
)

# 欲望：她想要的东西，不会主动喊出来，但会影响她怎么接话
DESIRE_POOL = (
    "想被人认真听一次",
    "想有个能一起骂两句的人",
    "想半天什么都不干",
    "想被人夸一句不是客套的",
    "想知道那件事到底怎么收场",
    "想让谁别再问了",
    "想把手头这摊收拾干净",
)

MAX_PRAISES = 40
MAX_DESIRES = 4


class SelfState:
    """读写 data/self.json。线程安全，读失败就返回默认值。"""

    def __init__(self, path: str | Path = "data/self.json") -> None:
        self.path = Path(path)
        self._lock = threading.RLock()
        if not str(path).endswith(":memory:"):
            self.path.parent.mkdir(parents=True, exist_ok=True)

    # ---------- 底层读写 ----------

    def _load(self) -> dict:
        try:
            raw = self.path.read_text(encoding="utf-8")
            data = json.loads(raw)
            if isinstance(data, dict):
                return data
        except (OSError, ValueError):
            pass
        return {}

    def _save(self, data: dict) -> None:
        data["updated"] = time.time()
        tmp = self.path.with_suffix(".json.tmp")
        try:
            tmp.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            os.replace(tmp, self.path)
        except OSError:
            pass

    # ---------- 情绪 ----------

    def set_mood(self, name: str, note: str = "") -> None:
        name = (name or "").strip()[:8]
        if not name:
            return
        with self._lock:
            data = self._load()
            data["mood"] = {"name": name, "note": (note or "").strip()[:40], "at": time.time()}
            self._save(data)

    def mood(self) -> tuple[str, str]:
        """返回 (情绪名, 起因)。"""
        with self._lock:
            data = self._load()
        item = data.get("mood") or {}
        if not isinstance(item, dict):
            return "", ""
        return str(item.get("name") or ""), str(item.get("note") or "")

    # ---------- 欲望 ----------

    def add_desire(self, what: str) -> None:
        what = (what or "").strip()[:30]
        if not what:
            return
        with self._lock:
            data = self._load()
            items = [d for d in (data.get("desires") or []) if isinstance(d, dict)]
            if any(str(d.get("what")) == what for d in items):
                return
            items.append({"what": what, "since": time.time(), "heat": 0.5})
            data["desires"] = items[-MAX_DESIRES:]
            self._save(data)

    def desires(self) -> list[str]:
        with self._lock:
            data = self._load()
        items = [d for d in (data.get("desires") or []) if isinstance(d, dict)]
        return [str(d.get("what")) for d in items if d.get("what")]

    def seed_desires_if_empty(self) -> None:
        """第一次运行时，给自己随便挑两三个想要的东西。"""
        with self._lock:
            data = self._load()
            if data.get("desires"):
                return
        import random

        picked = random.sample(DESIRE_POOL, k=2)
        for what in picked:
            self.add_desire(what)

    # ---------- 被夸 ----------

    def add_praise(self, text: str, who: str = "") -> None:
        text = (text or "").strip()[:200]
        if not text:
            return
        with self._lock:
            data = self._load()
            items = [p for p in (data.get("praises") or []) if isinstance(p, dict)]
            items.append({"text": text, "from": (who or "")[:24], "at": time.time()})
            data["praises"] = items[-MAX_PRAISES:]
            self._save(data)

    def praises(self, limit: int = 6) -> list[dict]:
        with self._lock:
            data = self._load()
        items = [p for p in (data.get("praises") or []) if isinstance(p, dict)]
        return items[-max(1, limit):]

    def praise_count(self) -> int:
        with self._lock:
            data = self._load()
        return len([p for p in (data.get("praises") or []) if isinstance(p, dict)])

    # ---------- 拼给模型看的一段 ----------

    def prompt_fragment(self) -> str:
        """把当前状态拼成一小段文字，塞进系统提示里。"""
        mood_name, mood_note = self.mood()
        want = self.desires()
        praised = self.praises(limit=5)

        lines: list[str] = []
        if mood_name:
            line = f"你现在的状态：{mood_name}"
            if mood_note:
                line += f"（{mood_note}）"
            lines.append(line)

        if want:
            lines.append("你心里惦记着的事：" + "；".join(want))

        if praised:
            recent = "；".join(
                f"{p.get('text', '')}"[:40] for p in praised if p.get("text")
            )
            if recent:
                lines.append("最近别人这样夸过你：" + recent)

        if not lines:
            return ""

        return (
            "\n\n你自己的状态（这些是你真实的态度，别直接念出来，让它影响你怎么说话）：\n"
            + "\n".join(f"- {line}" for line in lines)
        )

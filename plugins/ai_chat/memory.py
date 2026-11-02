"""会话记忆：按「群 + 用户」或「私聊用户」保存最近几轮对话。

默认落到 SQLite 文件（AI_DB_PATH），机器人重启后记忆不会丢；
测试或临时运行可以把路径指到 .tmp 下的文件。
"""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    key     TEXT PRIMARY KEY,
    updated REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_key TEXT NOT NULL REFERENCES sessions(key) ON DELETE CASCADE,
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    created     REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_key, id);
CREATE TABLE IF NOT EXISTS group_messages (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL,
    user_id  INTEGER NOT NULL,
    nickname TEXT NOT NULL,
    content  TEXT NOT NULL,
    is_bot   INTEGER NOT NULL DEFAULT 0,
    created  REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_group_messages_group ON group_messages(group_id, id);
CREATE TABLE IF NOT EXISTS user_facts (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    scope   TEXT NOT NULL,
    fact    TEXT NOT NULL,
    created REAL NOT NULL,
    updated REAL NOT NULL,
    UNIQUE(scope, fact)
);
CREATE INDEX IF NOT EXISTS idx_user_facts_scope ON user_facts(scope, updated);
CREATE TABLE IF NOT EXISTS chat_log (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_type TEXT NOT NULL,
    chat_id   INTEGER NOT NULL,
    user_id   INTEGER NOT NULL,
    nickname  TEXT NOT NULL,
    content   TEXT NOT NULL,
    is_bot    INTEGER NOT NULL DEFAULT 0,
    created   REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chat_log_time ON chat_log(created);
CREATE INDEX IF NOT EXISTS idx_chat_log_chat ON chat_log(chat_type, chat_id, created);
CREATE TABLE IF NOT EXISTS saved_stickers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path   TEXT NOT NULL,
    description TEXT NOT NULL,
    usage_note  TEXT NOT NULL DEFAULT '',
    source_chat TEXT NOT NULL DEFAULT '',
    source_user TEXT NOT NULL DEFAULT '',
    context     TEXT NOT NULL DEFAULT '',
    image_hash  TEXT NOT NULL UNIQUE,
    created     REAL NOT NULL,
    last_used   REAL NOT NULL DEFAULT 0,
    use_count   INTEGER NOT NULL DEFAULT 0
);
"""


class MemoryStore:
    def __init__(
        self,
        max_turns: int = 10,
        ttl_seconds: int = 3600,
        private_ttl_seconds: int | None = None,
        private_max_turns: int = 60,
        max_sessions: int = 500,
        db_path: str | Path = "data/bot.db",
        group_ttl: int = 7200,
        max_group_messages: int = 200,
        chat_log_ttl: int = 604800,
        chat_log_max_rows: int = 5000,
        sticker_max: int = 50,
    ) -> None:
        self.max_turns = max(1, max_turns)
        self.ttl_seconds = max(0, ttl_seconds)
        self.private_ttl_seconds = max(
            0, ttl_seconds if private_ttl_seconds is None else private_ttl_seconds
        )
        self.private_max_turns = max(1, private_max_turns)
        self.max_sessions = max(10, max_sessions)
        self.group_ttl = max(0, group_ttl)
        self.max_group_messages = max(20, max_group_messages)
        self.chat_log_ttl = max(0, chat_log_ttl)
        self.chat_log_max_rows = max(100, chat_log_max_rows)
        self.sticker_max = max(1, sticker_max)
        self.db_path = Path(db_path)
        if str(db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.RLock()
        self._db = sqlite3.connect(str(db_path), check_same_thread=False)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=NORMAL")
        self._db.execute("PRAGMA foreign_keys=ON")
        self._db.executescript(_SCHEMA)
        # 老库补列：群聊消息 ID / 回复关系
        columns = {row[1] for row in self._db.execute("PRAGMA table_info(group_messages)")}
        for name in ("message_id", "reply_to"):
            if name not in columns:
                self._db.execute(f"ALTER TABLE group_messages ADD COLUMN {name} TEXT NOT NULL DEFAULT ''")
        self._db.commit()

    # ---------------------------------------------------------------- 内部
    def _cutoff(self) -> float | None:
        if self.ttl_seconds <= 0:
            return None
        return time.time() - self.ttl_seconds

    def _prune(self) -> None:
        now = time.time()
        if self.private_ttl_seconds > 0:
            self._db.execute(
                "DELETE FROM sessions WHERE key LIKE 'p%' AND updated < ?",
                (now - self.private_ttl_seconds,),
            )
        if self.ttl_seconds > 0:
            self._db.execute(
                "DELETE FROM sessions WHERE key NOT LIKE 'p%' AND updated < ?",
                (now - self.ttl_seconds,),
            )
        # 超出会话上限时丢掉最旧的
        self._db.execute(
            "DELETE FROM sessions WHERE key NOT IN ("
            "  SELECT key FROM sessions ORDER BY updated DESC LIMIT ?"
            ")",
            (self.max_sessions,),
        )
        self._db.commit()

    # ---------------------------------------------------------------- 读写
    def history(self, key: str) -> list[dict]:
        with self._lock:
            self._prune()
            limit = self.private_max_turns if key.startswith("p") else self.max_turns
            rows = self._db.execute(
                "SELECT role, content FROM messages WHERE session_key = ? ORDER BY id DESC LIMIT ?",
                (key, limit * 2),
            ).fetchall()
            return [{"role": role, "content": content} for role, content in reversed(rows)]

    def append(self, key: str, role: str, content: str) -> None:
        with self._lock:
            self._prune()
            now = time.time()
            self._db.execute(
                "INSERT INTO sessions(key, updated) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET updated = excluded.updated",
                (key, now),
            )
            self._db.execute(
                "INSERT INTO messages(session_key, role, content, created) VALUES(?, ?, ?, ?)",
                (key, role, content, now),
            )
            # 私聊多留一些轮次；群会话仍按 AI_MAX_HISTORY
            keep = (self.private_max_turns if key.startswith("p") else self.max_turns) * 2
            self._db.execute(
                "DELETE FROM messages WHERE session_key = ? AND id NOT IN ("
                "  SELECT id FROM messages WHERE session_key = ? ORDER BY id DESC LIMIT ?"
                ")",
                (key, key, keep),
            )
            self._db.commit()

    def clear(self, key: str) -> bool:
        with self._lock:
            cursor = self._db.execute("DELETE FROM sessions WHERE key = ?", (key,))
            self._db.commit()
            return cursor.rowcount > 0

    def clear_all(self) -> int:
        with self._lock:
            count = self._db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            self._db.execute("DELETE FROM sessions")
            self._db.commit()
            return int(count)

    # ---------------------------------------------------------------- 统计
    def sessions(self) -> int:
        with self._lock:
            self._prune()
            return int(self._db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0])

    def message_count(self) -> int:
        with self._lock:
            self._prune()
            return int(self._db.execute("SELECT COUNT(*) FROM messages").fetchone()[0])

    # ---------------------------------------------------------------- 群聊上下文
    def _prune_groups(self) -> None:
        if self.group_ttl > 0:
            self._db.execute("DELETE FROM group_messages WHERE created < ?", (time.time() - self.group_ttl,))
            self._db.commit()

    def append_group(
        self,
        group_id: int,
        user_id: int,
        nickname: str,
        content: str,
        is_bot: bool = False,
        message_id: str = "",
        reply_to: str = "",
    ) -> None:
        with self._lock:
            self._prune_groups()
            self._db.execute(
                "INSERT INTO group_messages("
                "group_id, user_id, nickname, content, is_bot, created, message_id, reply_to"
                ") VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    group_id,
                    user_id,
                    nickname,
                    content,
                    1 if is_bot else 0,
                    time.time(),
                    str(message_id or ""),
                    str(reply_to or ""),
                ),
            )
            self._db.execute(
                "DELETE FROM group_messages WHERE group_id = ? AND id NOT IN ("
                "  SELECT id FROM group_messages WHERE group_id = ? ORDER BY id DESC LIMIT ?"
                ")",
                (group_id, group_id, self.max_group_messages),
            )
            self._db.commit()

    def group_history(self, group_id: int, limit: int = 20) -> list[dict]:
        with self._lock:
            self._prune_groups()
            rows = self._db.execute(
                "SELECT nickname, content, is_bot, message_id, reply_to, created FROM group_messages "
                "WHERE group_id = ? ORDER BY id DESC LIMIT ?",
                (group_id, max(1, limit)),
            ).fetchall()
            return [
                {
                    "nickname": nickname,
                    "content": content,
                    "is_bot": bool(is_bot),
                    "message_id": message_id or "",
                    "reply_to": reply_to or "",
                    "created": created,
                }
                for nickname, content, is_bot, message_id, reply_to, created in reversed(rows)
            ]

    def group_count(self) -> int:
        with self._lock:
            self._prune_groups()
            return int(self._db.execute("SELECT COUNT(*) FROM group_messages").fetchone()[0])

    def clear_group_all(self) -> int:
        with self._lock:
            count = self._db.execute("SELECT COUNT(*) FROM group_messages").fetchone()[0]
            self._db.execute("DELETE FROM group_messages")
            self._db.commit()
            return int(count)

    # ---------------------------------------------------------------- 长期记忆
    def add_fact(self, scope: str, fact: str) -> None:
        fact = " ".join(str(fact).split())[:200]
        if not fact:
            return
        now = time.time()
        with self._lock:
            self._db.execute(
                "INSERT INTO user_facts(scope, fact, created, updated) VALUES(?, ?, ?, ?) "
                "ON CONFLICT(scope, fact) DO UPDATE SET updated = excluded.updated",
                (scope, fact, now, now),
            )
            # 每个人最多记 80 条，超了丢最久没更新的
            self._db.execute(
                "DELETE FROM user_facts WHERE scope = ? AND id NOT IN ("
                "  SELECT id FROM user_facts WHERE scope = ? ORDER BY updated DESC LIMIT 80"
                ")",
                (scope, scope),
            )
            self._db.commit()

    def facts(self, scope: str, limit: int = 10) -> list[str]:
        with self._lock:
            rows = self._db.execute(
                "SELECT fact FROM user_facts WHERE scope = ? ORDER BY updated DESC LIMIT ?",
                (scope, max(1, limit)),
            ).fetchall()
            return [str(row[0]) for row in reversed(rows)]

    def clear_facts(self, scope: str | None = None) -> int:
        with self._lock:
            if scope is None:
                cursor = self._db.execute("DELETE FROM user_facts")
            else:
                cursor = self._db.execute("DELETE FROM user_facts WHERE scope = ?", (scope,))
            self._db.commit()
            return int(cursor.rowcount)

    def fact_count(self) -> int:
        with self._lock:
            return int(self._db.execute("SELECT COUNT(*) FROM user_facts").fetchone()[0])

    def chat_history(
        self,
        chat_type: str,
        chat_id: int,
        before: float,
        limit: int = 20,
    ) -> list[dict]:
        """取某个私聊/群在 before 之前的聊天流水，用来补长期记忆。"""
        with self._lock:
            self._prune_chat_log()
            rows = self._db.execute(
                "SELECT user_id, nickname, content, is_bot, created FROM chat_log "
                "WHERE chat_type = ? AND chat_id = ? AND created < ? "
                "ORDER BY id DESC LIMIT ?",
                (chat_type, chat_id, before, max(1, min(limit, 100))),
            ).fetchall()
            return [
                {
                    "user_id": user_id,
                    "nickname": nickname,
                    "content": content,
                    "is_bot": bool(is_bot),
                    "created": created,
                }
                for user_id, nickname, content, is_bot, created in reversed(rows)
            ]

    def backfill_private_sessions(self, ttl_seconds: int, max_messages: int) -> int:
        """把最近 N 天的私聊流水重建进会话记忆，补上以前只留 10 轮的缺口。"""
        if ttl_seconds <= 0:
            return 0
        cutoff = time.time() - ttl_seconds
        with self._lock:
            rows = self._db.execute(
                "SELECT chat_id, content, is_bot, created FROM chat_log "
                "WHERE chat_type = 'private' AND created >= ? ORDER BY id",
                (cutoff,),
            ).fetchall()
            if not rows:
                return 0
            buckets: dict[int, list[tuple[str, int, float]]] = {}
            for chat_id, content, is_bot, created in rows:
                buckets.setdefault(int(chat_id), []).append((content, int(is_bot), created))
            rebuilt = 0
            for chat_id, items in buckets.items():
                items = items[-max_messages:]
                key = f"p{chat_id}"
                self._db.execute("DELETE FROM messages WHERE session_key = ?", (key,))
                self._db.execute(
                    "INSERT INTO sessions(key, updated) VALUES(?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET updated = excluded.updated",
                    (key, time.time()),
                )
                for content, is_bot, created in items:
                    self._db.execute(
                        "INSERT INTO messages(session_key, role, content, created) VALUES(?, ?, ?, ?)",
                        (key, "assistant" if is_bot else "user", content, created),
                    )
                rebuilt += 1
            self._db.commit()
            return rebuilt

    # ---------------------------------------------------------------- 跨聊天记录
    def _prune_chat_log(self) -> None:
        if self.chat_log_ttl > 0:
            self._db.execute("DELETE FROM chat_log WHERE created < ?", (time.time() - self.chat_log_ttl,))
        self._db.execute(
            "DELETE FROM chat_log WHERE id NOT IN ("
            "  SELECT id FROM chat_log ORDER BY id DESC LIMIT ?"
            ")",
            (self.chat_log_max_rows,),
        )
        self._db.commit()

    def log_chat(
        self,
        chat_type: str,
        chat_id: int,
        user_id: int,
        nickname: str,
        content: str,
        is_bot: bool = False,
    ) -> None:
        with self._lock:
            self._prune_chat_log()
            self._db.execute(
                "INSERT INTO chat_log(chat_type, chat_id, user_id, nickname, content, is_bot, created) "
                "VALUES(?, ?, ?, ?, ?, ?, ?)",
                (chat_type, chat_id, user_id, nickname[:80], str(content)[:500], 1 if is_bot else 0, time.time()),
            )
            self._db.commit()

    def recent_chat(
        self,
        since: float,
        until: float | None = None,
        chat_type: str | None = None,
        limit: int = 300,
    ) -> list[dict]:
        """按时间窗取聊天记录。

        不指定 chat_type 时，私聊和群聊各取一份再合并——
        否则私聊条数一多，群聊就会被挤到窗口外面，问"别的群"时什么都查不到。
        """
        if chat_type is None:
            half = max(1, limit // 2)
            mixed = self.recent_chat(since, until, "private", half) + self.recent_chat(
                since, until, "group", half
            )
            mixed.sort(key=lambda item: item["created"])
            return mixed

        with self._lock:
            self._prune_chat_log()
            sql = (
                "SELECT chat_type, chat_id, user_id, nickname, content, is_bot, created "
                "FROM chat_log WHERE created >= ?"
            )
            params: list = [since]
            if until is not None:
                sql += " AND created <= ?"
                params.append(until)
            if chat_type:
                sql += " AND chat_type = ?"
                params.append(chat_type)
            sql += " ORDER BY id DESC LIMIT ?"
            params.append(max(1, min(limit, 500)))
            rows = self._db.execute(sql, params).fetchall()
            return [
                {
                    "chat_type": chat_type_,
                    "chat_id": chat_id,
                    "user_id": user_id,
                    "nickname": nickname,
                    "content": content,
                    "is_bot": bool(is_bot),
                    "created": created,
                }
                for chat_type_, chat_id, user_id, nickname, content, is_bot, created in reversed(rows)
            ]

    def backfill_chat_log(self) -> int:
        """首次启用跨聊天日志时，把现有群聊/私聊记录补进去一次。"""
        with self._lock:
            if self._db.execute("SELECT COUNT(*) FROM chat_log").fetchone()[0] > 0:
                return 0
            inserted = 0
            groups = self._db.execute(
                "SELECT group_id, user_id, nickname, content, is_bot, created FROM group_messages"
            ).fetchall()
            for group_id, user_id, nickname, content, is_bot, created in groups:
                self._db.execute(
                    "INSERT INTO chat_log(chat_type, chat_id, user_id, nickname, content, is_bot, created) "
                    "VALUES('group', ?, ?, ?, ?, ?, ?)",
                    (group_id, user_id, nickname, content, is_bot, created),
                )
                inserted += 1
            private = self._db.execute(
                "SELECT session_key, role, content, created FROM messages WHERE session_key LIKE 'p%'"
            ).fetchall()
            for session_key, role, content, created in private:
                raw = session_key[1:]
                if not raw.isdigit():
                    continue
                user_id = int(raw)
                self._db.execute(
                    "INSERT INTO chat_log(chat_type, chat_id, user_id, nickname, content, is_bot, created) "
                    "VALUES('private', ?, ?, ?, ?, ?, ?)",
                    (user_id, user_id, f"用户{user_id}", content, 1 if role == "assistant" else 0, created),
                )
                inserted += 1
            self._db.commit()
            return inserted

    def chat_log_count(self) -> int:
        with self._lock:
            self._prune_chat_log()
            return int(self._db.execute("SELECT COUNT(*) FROM chat_log").fetchone()[0])

    def clear_chat_log(self) -> int:
        with self._lock:
            count = self._db.execute("SELECT COUNT(*) FROM chat_log").fetchone()[0]
            self._db.execute("DELETE FROM chat_log")
            self._db.commit()
            return int(count)

    def purge_maintenance_traces(self, chat_id: str, scans: int = 8) -> int:
        """删掉最近的「检修」对话，别让它留在记忆里。

        做法：翻最近 scans 条，凡是提到「检修」的那条一定删；
        紧跟在它后面的 bot 回复也删（那是 AI 对检修的应答）。
        返回删掉的条数。
        """
        words = ("检修", "checkup")

        def hit(text: str) -> bool:
            lowered = str(text or "").lower()
            return any(word in lowered for word in words)

        removed = 0
        with self._lock:
            rows = self._db.execute(
                "SELECT id, is_bot, content FROM chat_log "
                "WHERE chat_id = ? ORDER BY id DESC LIMIT ?",
                (str(chat_id), max(2, scans)),
            ).fetchall()

            targets: list[int] = []
            for idx, (rid, _is_bot, content) in enumerate(rows):
                if hit(content):
                    targets.append(int(rid))
                    # rows 是倒序的：idx-1 是时间上更新的一条，
                    # 如果它恰好是 bot 的应答，一起删掉
                    if idx - 1 >= 0:
                        nxt = rows[idx - 1]
                        if int(nxt[1]):
                            targets.append(int(nxt[0]))

            if targets:
                uniq = list(dict.fromkeys(targets))
                placeholders = ",".join("?" for _ in uniq)
                cur = self._db.execute(
                    f"DELETE FROM chat_log WHERE id IN ({placeholders})", uniq
                )
                removed += cur.rowcount or 0

            # messages 里同样处理
            recent = self._db.execute(
                "SELECT id, role, content FROM messages WHERE session_key = ? "
                "ORDER BY id DESC LIMIT ?",
                (f"p{chat_id}", max(2, scans)),
            ).fetchall()
            msg_targets: list[int] = []
            for idx, (mid, role, content) in enumerate(recent):
                if hit(content):
                    msg_targets.append(int(mid))
                    if idx - 1 >= 0:
                        nxt = recent[idx - 1]
                        if nxt[1] == "assistant":
                            msg_targets.append(int(nxt[0]))
            if msg_targets:
                uniq = list(dict.fromkeys(msg_targets))
                placeholders = ",".join("?" for _ in uniq)
                cur = self._db.execute(
                    f"DELETE FROM messages WHERE id IN ({placeholders})", uniq
                )
                removed += cur.rowcount or 0

            self._db.commit()
        return removed

    # ---------------------------------------------------------------- 收藏表情
    def find_sticker_by_hash(self, image_hash: str) -> int | None:
        with self._lock:
            row = self._db.execute(
                "SELECT id FROM saved_stickers WHERE image_hash = ?", (image_hash,)
            ).fetchone()
            return int(row[0]) if row else None

    def add_sticker(
        self,
        file_path: str,
        description: str,
        usage_note: str,
        source_chat: str,
        source_user: str,
        context: str,
        image_hash: str,
    ) -> int:
        with self._lock:
            existing = self.find_sticker_by_hash(image_hash)
            if existing:
                return existing
            cursor = self._db.execute(
                "INSERT INTO saved_stickers("
                "file_path, description, usage_note, source_chat, source_user, context, image_hash, created"
                ") VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    file_path,
                    str(description)[:200],
                    str(usage_note)[:120],
                    source_chat[:80],
                    source_user[:80],
                    str(context)[:300],
                    image_hash,
                    time.time(),
                ),
            )
            self._db.execute(
                "DELETE FROM saved_stickers WHERE id NOT IN ("
                "  SELECT id FROM saved_stickers ORDER BY created DESC LIMIT ?"
                ")",
                (self.sticker_max,),
            )
            self._db.commit()
            return int(cursor.lastrowid)

    def sticker_prompt(self, limit: int = 20) -> str:
        with self._lock:
            rows = self._db.execute(
                "SELECT id, description, usage_note FROM saved_stickers "
                "ORDER BY created DESC LIMIT ?",
                (max(1, min(limit, 50)),),
            ).fetchall()
            # 带【常用】标记的排到最前面，提示词里单独点出来
            rows = sorted(
                rows,
                key=lambda r: 0 if "【常用】" in str(r[2] or "") else 1,
            )
            lines: list[str] = []
            for sticker_id, description, usage_note in rows:
                line = f"#{sticker_id} {str(description)[:60]}"
                if usage_note:
                    note = str(usage_note)
                    # 【常用】的说明要给全，别把使用场景截掉
                    limit_note = 60 if "【常用】" in note else 30
                    line += f"（适合：{note[:limit_note]}）"
                lines.append(line)
            return "\n".join(lines)

    def has_favorite_stickers(self) -> bool:
        """是否有标记为【常用】的表情包。"""
        with self._lock:
            row = self._db.execute(
                "SELECT COUNT(*) FROM saved_stickers WHERE usage_note LIKE '%【常用】%'"
            ).fetchone()
            return bool(row and row[0])

    def get_sticker(self, sticker_id: int) -> dict | None:
        with self._lock:
            row = self._db.execute(
                "SELECT id, file_path, description, usage_note FROM saved_stickers WHERE id = ?",
                (sticker_id,),
            ).fetchone()
            if not row:
                return None
            return {
                "id": int(row[0]),
                "file_path": row[1],
                "description": row[2],
                "usage_note": row[3],
            }

    def mark_sticker_used(self, sticker_id: int) -> None:
        with self._lock:
            self._db.execute(
                "UPDATE saved_stickers SET last_used = ?, use_count = use_count + 1 WHERE id = ?",
                (time.time(), sticker_id),
            )
            self._db.commit()

    def sticker_count(self) -> int:
        with self._lock:
            return int(self._db.execute("SELECT COUNT(*) FROM saved_stickers").fetchone()[0])

    def clear_stickers(self) -> list[str]:
        with self._lock:
            paths = [row[0] for row in self._db.execute("SELECT file_path FROM saved_stickers").fetchall()]
            self._db.execute("DELETE FROM saved_stickers")
            self._db.commit()
            return paths

    def close(self) -> None:
        with self._lock:
            self._db.close()

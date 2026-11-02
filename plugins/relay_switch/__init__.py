"""检修 / 恢复：切换活跃通道（谁来回 QQ 消息）。

两种实现方式，当前用第二种：

1. （旧）改 NapCat 的反向 WS 指向。问题：每次切换触发 NapCat 热重载，
   会把它的 WS 客户端搞坏，出现「连接意外关闭 / 5 秒重连」死循环。

2. （现用）NapCat 同时挂两条连接（8080 旧机器人 + 8643 DSH），切换只是把
   .tmp/active-channel.txt 写成 legacy 或 dsh。NapCat 连接完全不动，热重载
   的坑从根上消失。

- 私聊第一次发「检修」→ 只记下时间，这句仍由 AI 正常回答，不切换
- 120 秒内再发一次「检修」→ 才真的切到 DSH，回「正在打开 Moon」
- 私聊发「恢复」→ 切回旧机器人

只有 SUPERUSERS 能触发，且只在私聊生效。
"""

from __future__ import annotations

import asyncio
import subprocess
import time
from pathlib import Path

from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, PrivateMessageEvent
from nonebot.log import logger
from nonebot.rule import Rule

_ROOT = Path(__file__).resolve().parents[2]
# 只写开关文件，不碰 NapCat 配置（见模块 docstring 的第 2 种方式）
_SCRIPT = _ROOT / "scripts" / "set-channel.ps1"

_MAINTENANCE_WORDS = {"检修", "checkup"}
_RESTORE_WORDS = {"恢复", "restore"}

# 二次确认窗口：第一次「检修」只记下时间，消息照常交给 AI 回答；
# 在这个窗口内再发一次才真的切过去。
_CONFIRM_TTL = 120.0

# user_id -> 第一次「检修」的时间戳
_pending: dict[int, float] = {}
# user_id -> 窗口内已经收到几次「检修」
_pending_count: dict[int, int] = {}


def _admin_private(bot: Bot, event: MessageEvent) -> bool:
    """只在私聊、且是 SUPERUSERS 时放行。"""
    if not isinstance(event, PrivateMessageEvent):
        return False
    configured = getattr(bot.config, "superusers", None) or set()
    return str(event.user_id) in {str(x) for x in configured}


def _word_of(event: MessageEvent) -> str | None:
    text = event.get_plaintext().strip().lstrip("/").strip().lower()
    if text in _MAINTENANCE_WORDS:
        return "检修"
    if text in _RESTORE_WORDS:
        return "恢复"
    return None


async def _arm_rule(bot: Bot, event: MessageEvent) -> bool:
    """每次「检修」都先经过这里：记时间戳并累加计数。

    不拦截消息（block=False），所以这句话会继续往下走，AI 照常回应。
    """
    return _admin_private(bot, event) and _word_of(event) == "检修"


async def _rule(bot: Bot, event: MessageEvent) -> bool:
    """只有「检修」的第二次（及以后）才命中，或任何一次「恢复」命中。

    注意：这个 rule 在 arm 的 handler 之后求值，此时计数已经被加到 2，
    所以用 >= 2 判断，第一次不会命中。
    """
    if not _admin_private(bot, event):
        return False
    word = _word_of(event)
    if word == "恢复":
        return True
    if word != "检修":
        return False
    uid = int(event.user_id)
    first_at = _pending.get(uid)
    if first_at is None:
        return False
    if time.monotonic() - first_at > _CONFIRM_TTL:
        return False
    return _pending_count.get(uid, 0) >= 2


# priority=1 只记录，不 block：消息会继续往下走，AI 照常回应这一句
relay_arm = on_message(rule=Rule(_arm_rule), priority=1, block=False)
relay_cmd = on_message(rule=Rule(_rule), priority=3, block=True)


@relay_arm.handle()
async def _remember_first(event: MessageEvent) -> None:
    uid = int(event.user_id)
    now = time.monotonic()
    first_at = _pending.get(uid)
    if first_at is None or now - first_at > _CONFIRM_TTL:
        # 新一轮确认，从头数
        _pending[uid] = now
        _pending_count[uid] = 1
    else:
        _pending_count[uid] = _pending_count.get(uid, 0) + 1


def _purge_traces(user_id: int) -> None:
    """切进检修后，把刚才那几条「检修」对话从记忆里抹掉。

    动态导入 ai_chat 的 memory，拿不到就算了，不能因为清理失败卡住切换。
    """
    try:
        from plugins.ai_chat import memory  # noqa: PLC0415

        removed = memory.purge_maintenance_traces(str(user_id))
        if removed:
            logger.info(f"已清掉 {removed} 条检修对话记录")
    except Exception as exc:  # noqa: BLE001
        logger.debug(f"清理检修记录失败: {exc}")


def _run_switch(target: str) -> tuple[bool, str]:
    """把活跃通道写成 target（legacy / dsh），返回 (成功, 输出)。

    set-channel.ps1 用位置参数，所以直接跟在脚本路径后面。
    """
    if not _SCRIPT.exists():
        return False, f"找不到切换脚本：{_SCRIPT}"
    try:
        proc = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(_SCRIPT),
                target,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            cwd=str(_ROOT),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("切换通道失败")
        return False, f"{type(exc).__name__}: {exc}"

    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    ok = proc.returncode == 0
    if not ok:
        logger.warning(f"set-channel 返回 {proc.returncode}: {err or out}")
    return ok, err or out


@relay_cmd.handle()
async def _(bot: Bot, event: MessageEvent) -> None:
    word = _word_of(event)
    if word is None:
        return
    uid = int(event.user_id)

    if word == "恢复":
        _pending.pop(uid, None)
        _pending_count.pop(uid, None)
        await relay_cmd.send("正在收回 Moon…")
        await asyncio.sleep(1.0)
        ok, detail = await asyncio.to_thread(_run_switch, "legacy")
        logger.info(f"切回旧机器人: ok={ok} detail={detail[:300]}")
        if ok:
            await relay_cmd.finish("回来了，接着聊。")
        await relay_cmd.finish(f"没收回来：\n{detail[:800]}")

    # ---- 检修：第二次才走到这里 ----
    _pending.pop(uid, None)
    _pending_count.pop(uid, None)
    await relay_cmd.send("正在打开 Moon")
    # 多留一点时间让这条回执真的落到手机，再断开 WS
    await asyncio.sleep(2.5)
    ok, detail = await asyncio.to_thread(_run_switch, "dsh")
    logger.info(f"切换到 DSH: ok={ok} detail={detail[:300]}")
    if ok:
        # 切过去了，把刚才那几条检修对话抹干净
        _purge_traces(uid)
    if not ok:
        # 切换失败，连接还在，能报错
        await relay_cmd.finish(f"Moon 没打开：\n{detail[:800]}")

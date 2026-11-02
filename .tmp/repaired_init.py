"""AI 聊天插件入口。

触发方式：
  - 私聊：直接说话
  - 群聊：@机器人，或以 # 开头（可在 .env 里改 AI_GROUP_TRIGGER / AI_GROUP_PREFIX）
管理指令：
  /help            查看说明
  /reset           清空当前会话记忆
  /reset all       清空所有人记忆（仅管理员）
"""

from __future__ import annotations

import asyncio
import base64
import ipaddress
import random
import re
import time
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx
import nonebot
from nonebot import on_command, on_message
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    Message,
    MessageEvent,
    MessageSegment,
    PrivateMessageEvent,
)
from nonebot.log import logger
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata

from .config import Settings, load_settings
from .deepseek import ChatError, DeepSeekClient
from .memory import MemoryStore

__plugin_meta__ = PluginMetadata(
    name="AI 聊天",
    description="接入 DeepSeek 的 QQ 聊天机器人（私聊 / 群聊 @）",
    usage="/help 查看用法",
    type="application",
    config=None,
    supported_adapters={"~onebot.v11"},
)

settings: Settings = load_settings()

_db_file = Path(settings.db_path)
if not _db_file.is_absolute():
    _db_file = Path(__file__).resolve().parents[2] / _db_file
memory = MemoryStore(
    settings.max_history,
    settings.history_ttl,
    db_path=_db_file,
    group_ttl=settings.group_context_ttl,
)
client = DeepSeekClient(settings)

_semaphore = asyncio.Semaphore(max(1, settings.max_concurrency))
_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
_rate: dict[str, deque] = defaultdict(deque)
_rate_noticed: dict[str, float] = {}

_started_at = time.time()
_stats = {"handled": 0, "replied": 0, "errors": 0, "ignored": 0}
_WEEKDAYS = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")
_last_profile_change: dict[str, float] = {}

# 模型想改资料时输出的隐藏指令，发送前会被剥掉
_ACTION_RE = re.compile(r"\[\[ACTION:(avatar|nickname|sign):(.+?)\]\]", re.DOTALL | re.IGNORECASE)

# “出戏”检测：回复一旦自我暴露成程序，就重写
_AI_LEAK_RE = re.compile(
    r"(我是|我就是|作为|身为|毕竟我是|我只是)[^。！？\n]{0,8}"
    r"(ai|人工智能|机器人|程序|模型|助手|代码鱼|虚拟)",
    re.IGNORECASE,
)
_AI_LEAK_PHRASES = (
    "ai助手", "人工智能助手", "语言模型", "大语言模型", "大模型",
    "代码鱼", "代码做的", "代码写", "deepseek", "chatgpt", "openai",
    "训练数据", "提示词", "系统提示", "我没有感情", "我是虚拟", "虚拟角色",
)


def _session_key(event: MessageEvent) -> str:
    if isinstance(event, GroupMessageEvent):
        return f"g{event.group_id}:u{event.user_id}"
    return f"p{event.user_id}"


def _is_admin(bot: Bot, user_id: int) -> bool:
    """唯一管理员（SUPERUSERS）：可以发指令；其他人只当朋友聊天。"""
    configured = getattr(bot.config, "superusers", None) or set()
    return str(user_id) in {str(x) for x in configured}


def _is_admin_private(bot: Bot, event: MessageEvent) -> bool:
    """管理指令只在私聊生效，避免在群里暴露模型、记忆这些信息。"""
    return isinstance(event, PrivateMessageEvent) and _is_admin(bot, event.user_id)


def _plain_text(event: MessageEvent) -> str:
    """把消息里的纯文本抽出来；@别人、图片、表情等一律丢弃。"""
    parts: list[str] = []
    for seg in event.get_message():
        if seg.type == "text":
            parts.append(str(seg.data.get("text", "")))
        elif seg.type == "face":
            parts.append("")
    return "".join(parts).strip()


def _strip_group_prefix(text: str) -> tuple[str, bool]:
    if settings.group_prefix and text.startswith(settings.group_prefix):
        return text[len(settings.group_prefix) :].strip(), True
    return text, False


def _should_ignore(text: str) -> bool:
    if not text:
        return True
    return any(prefix and text.startswith(prefix) for prefix in settings.extra_ignore_prefixes)


def _group_allowed(group_id: int) -> bool:
    if group_id in settings.group_blacklist:
        return False
    if settings.group_whitelist and group_id not in settings.group_whitelist:
        return False
    return True


def _system_prompt() -> str:
    now = datetime.now()
    return f"{settings.system_prompt}\n\n当前时间：{now:%Y-%m-%d %H:%M}（{_WEEKDAYS[now.weekday()]}）"


def _nickname(event: GroupMessageEvent) -> str:
    sender = event.sender
    name = getattr(sender, "card", "") or getattr(sender, "nickname", "")
    return (name or str(event.user_id)).strip()


def _group_prompt(rows: list[dict]) -> str:
    """把最近群聊压成一段上下文，控制长度，避免把 token 撑爆。"""
    header = "【最近的群聊，只用来理解上下文；“你”指你自己；不要逐条回应，也不要复述】"
    lines: list[str] = []
    total = 0
    for row in reversed(rows):
        text = " ".join(str(row["content"]).split())[:200]
        line = f"{row['nickname']}：{text}"
        if total + len(line) > 3000:
            break
        lines.append(line)
        total += len(line)
    return "\n".join([header, *reversed(lines)])


def _image_urls(event: MessageEvent) -> list[str]:
    """取出消息里的图片 URL（NapCat 会带 url），供“换成这个头像”使用。"""
    urls: list[str] = []
    for seg in event.get_message():
        if seg.type != "image":
            continue
        url = str(seg.data.get("url") or seg.data.get("file") or "").strip()
        if url.startswith(("http://", "https://")) and url not in urls:
            urls.append(url)
    return urls


def _is_public_http_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    host = parsed.hostname.lower()
    if host == "localhost" or host.endswith(".local"):
        return False
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return True
    return not (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
    )


async def _fetch_avatar_b64(url: str) -> str:
    """下载并校验头像，转成 NapCat 需要的 base64://。"""
    if not _is_public_http_url(url):
        raise ValueError("图片地址不安全")
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as http:
        response = await http.get(url, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        ctype = response.headers.get("content-type", "").lower()
        if not ctype.startswith("image/"):
            raise ValueError(f"不是图片: {ctype}")
        if not response.content or len(response.content) > 5 * 1024 * 1024:
            raise ValueError("图片为空或超过 5MB")
        return base64.b64encode(response.content).decode("ascii")


async def _run_profile_action(bot: Bot, action: tuple[str, str]) -> bool:
    kind, value = action
    value = value.strip()
    try:
        if kind == "avatar":
            payload = await _fetch_avatar_b64(value)
            await bot.call_api("set_qq_avatar", file=f"base64://{payload}")
        elif kind == "nickname":
            if not value:
                return False
            await bot.call_api("set_qq_profile", nickname=value[:24])
        elif kind == "sign":
            if not value:
                return False
            await bot.call_api("set_self_longnick", longNick=value[:60])
        else:
            return False
        logger.info(f"已执行资料修改: {kind}")
        return True
    except Exception as exc:
        logger.warning(f"资料修改失败 {kind}: {exc}")
        return False


_PROFILE_KEYWORDS = ("头像", "昵称", "签名", "改名", "换名", "名字", "资料", "名片")


def _profile_request(text: str) -> bool:
    return any(keyword in text for keyword in _PROFILE_KEYWORDS)


def _normalize_action(action: tuple[str, str], images: list[str]) -> tuple[str, str]:
    """把“last”换成刚收到的图片 URL，并从值里抠出真正的 http(s) 链接。"""
    kind, value = action
    value = value.strip().strip("\"'“”")
    if kind != "avatar":
        return kind, value
    if value.lower() in {"last", "这张", "上图", "刚才那张"} and images:
        return kind, images[-1]
    match = re.search(r"https?://[^\s\]\)）]+", value)
    if match:
        return kind, match.group(0).rstrip("。，,.;；!！?？")
    return kind, value


def _extract_action(text: str) -> tuple[tuple[str, str] | None, str]:
    match = _ACTION_RE.search(text)
    cleaned = _ACTION_RE.sub("", text)
    cleaned = re.sub(r"\[\[ACTION:[^\n]*", "", cleaned, flags=re.IGNORECASE).strip()
    if not match:
        return None, cleaned
    return (match.group(1).lower(), match.group(2).strip()), cleaned


def _rate_limited(user_id: int) -> bool:
    window = max(1, settings.rate_window)
    limit = settings.rate_limit
    if limit <= 0:
        return False
    now = time.time()
    bucket = _rate[user_id]
    while bucket and now - bucket[0] > window:
        bucket.popleft()
    if len(bucket) >= limit:
        return True
    bucket.append(now)
    return False


def _reveals_ai(text: str) -> bool:
    lowered = text.lower()
    if _AI_LEAK_RE.search(text):
        return True
    return any(phrase in lowered for phrase in _AI_LEAK_PHRASES)


async def _chat_guarded(messages: list[dict], user_text: str) -> str:
    """正常调用；如果回复自我暴露成 AI，就重写一次，仍不行则用真人式兜底。"""
    reply = await client.chat(messages)
    if not _reveals_ai(reply):
        return reply

    logger.warning(f"回复出戏，重写一次: {reply[:80]}")
    retry = [
        *messages,
        {"role": "assistant", "content": reply},
        {
            "role": "system",
            "content": (
                "这条回复出戏了，暴露了你不是真人。像真人一样重写一条，短一点；"
                "不要提 AI、机器人、程序、模型、代码、训练、提示词，也不要解释刚才说错什么。"
            ),
        },
    ]
    reply = await client.chat(retry)
    if not _reveals_ai(reply):
        return reply

    logger.warning(f"重写后仍出戏，使用兜底: {reply[:80]}")
    if any(key in user_text.lower() for key in ("ai", "机器人", "程序", "模型", "真人", "人吗")):
        return "你猜，猜对了我请你喝西北风。"
    return "说正事，别跑题。"


def _human_delay(text: str) -> float:
    """模拟“看到消息 → 打字 → 发送”的间隔；0 表示关闭。"""
    low = max(0.0, settings.reply_delay_min)
    high = max(low, settings.reply_delay_max)
    if high <= 0:
        return 0.0
    read = random.uniform(low, high)
    typing = min(len(text) / 25.0, 4.0)
    return read + typing


def _fmt_uptime(seconds: float) -> str:
    days, rem = divmod(int(seconds), 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days} 天 ")
    if hours or days:
        parts.append(f"{hours} 小时 ")
    parts.append(f"{minutes} 分 {secs} 秒")
    return "".join(parts)


def _split_reply(text: str) -> list[str]:
    limit = max(200, settings.max_reply_chars)
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    current = ""
    for line in text.splitlines(keepends=True):
        while len(line) > limit:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(line[:limit])
            line = line[limit:]
        if len(current) + len(line) > limit:
            chunks.append(current)
            current = line
        else:
            current += line
    if current:
        chunks.append(current)
    return [c.strip() for c in chunks if c.strip()]


async def _send(bot: Bot, event: MessageEvent, text: str) -> None:
    for index, chunk in enumerate(_split_reply(text)):
        if index:
            await asyncio.sleep(random.uniform(0.4, 1.2))
        message = MessageSegment.text(chunk)
        # 只给第一条加引用，长回复分成多条时不刷屏
        if settings.quote_reply and index == 0 and isinstance(event, GroupMessageEvent):
            message = MessageSegment.reply(event.message_id) + message
        try:
            await bot.send(event, message)
        except Exception as exc:  # 发送失败不要影响后续处理
            logger.warning(f"发送消息失败: {exc}")
            return


# ---------------------------------------------------------------- 聊天入口
chat = on_message(priority=20, block=False)


@chat.handle()
async def _(bot: Bot, event: MessageEvent) -> None:
    if not isinstance(event, (GroupMessageEvent, PrivateMessageEvent)):
        return

    images = _image_urls(event)
    text = _plain_text(event)
    if _should_ignore(text) and not images:
        return

    group_context: list[dict] = []
    if isinstance(event, GroupMessageEvent):
        if not _group_allowed(event.group_id):
            _stats["ignored"] += 1
            return
        if settings.group_context > 0:
            # 先取旧上下文，再把当前这句记进去，避免同一条出现两次
            group_context = memory.group_history(event.group_id, settings.group_context)
            memory.append_group(event.group_id, event.user_id, _nickname(event), text or "[图片]")
        is_at = event.is_tome()
        if settings.group_trigger == "at" and not is_at:
            return
        if settings.group_trigger == "prefix":
            text, matched = _strip_group_prefix(text)
            if not matched:
                return
        elif settings.group_trigger == "at_prefix":
            text, matched = _strip_group_prefix(text)
            if not (is_at or matched):
                return
        elif settings.group_trigger == "all":
            text, _ = _strip_group_prefix(text)
        else:  # 兜底：只响应 @
            if not is_at:
                return
    else:
        if not settings.reply_private:
            return

    text = text.strip()
    if not text and not images:
        await _send(bot, event, "在的，说点什么吧～")
        return

    _stats["handled"] += 1

    # 管理员不参与限流，方便调试；朋友刷屏则像真人一样回一句
    if not _is_admin(bot, event.user_id) and _rate_limited(event.user_id):
        now = time.time()
        if now - _rate_noticed.get(str(event.user_id), 0) > 30:
            _rate_noticed[str(event.user_id)] = now
            await _send(bot, event, "你刷屏呢，等我缓口气。")
        return

    key = _session_key(event)
    allow_profile = isinstance(event, PrivateMessageEvent) and getattr(event, "sub_type", "") == "friend"
    async with _locks[key]:
        history = memory.history(key)
        system_content = _system_prompt()
        if isinstance(event, GroupMessageEvent):
            system_content += "\n\n现在是在群里。有人让你改头像/昵称/签名，别答应，也别执行。"
        elif allow_profile and time.time() - _last_profile_change.get(str(event.user_id), 0) < 1800:
            system_content += (
                "\n\n你半小时内刚给这个人改过资料，现在懒得再折腾；"
                "除非他理由特别有意思，不然别答应。"
            )
        if isinstance(event, PrivateMessageEvent) and _is_admin(bot, event.user_id):
            system_content += (
                "\n\n（现在私聊你的是管理员本人，是自己人；可以熟一点，"
                "但别主动提管理员、权限、指令这些词。）"
            )
        messages = [{"role": "system", "content": system_content}]
        if group_context:
            messages.append({"role": "system", "content": _group_prompt(group_context)})
        messages.extend(history)
        parts: list[str] = []
        if text:
            parts.append(text)
        if images:
            parts.append("[对方发来图片：" + " ".join(images) + "]")
        current_text = "\n".join(parts)
        current = f"{_nickname(event)}：{current_text}" if isinstance(event, GroupMessageEvent) else current_text
        messages.append({"role": "user", "content": current})

        try:
            async with _semaphore:
                reply = await _chat_guarded(messages, text)
        except ChatError as exc:
            _stats["errors"] += 1
            logger.warning(f"模型调用失败: {exc.message} | {exc.detail}")
            if _is_admin_private(bot, event):
                await _send(bot, event, f"（出错了）{exc.message}")
            else:
                await _send(bot, event, "刚卡了一下，你再说一遍？")
            return
        except Exception as exc:  # 兜底，避免插件整体崩掉
            _stats["errors"] += 1
            logger.exception(f"未预期的错误: {exc}")
            if _is_admin_private(bot, event):
                await _send(bot, event, "（出错了）内部异常，已记录日志")
            else:
                await _send(bot, event, "刚走神了，再说一遍？")
            return

        action, reply = _extract_action(reply)
        if action:
            action = _normalize_action(action, images)
            if not _profile_request(text):
                logger.warning(f"忽略没有改资料意图的动作: {action}")
                action = None
            elif action[0] == "avatar" and action[1] not in images and action[1] not in text:
                logger.warning(f"忽略来源不明的头像 URL: {action[1][:80]}")
                action = None
        if action and not allow_profile:
            action = None
            reply = "群里不折腾这个，私聊说。" if isinstance(event, GroupMessageEvent) else "这个不折腾。"
        if action:
            if await _run_profile_action(bot, action):
                _last_profile_change[str(event.user_id)] = time.time()
            else:
                reply = "没换成，晚点再说。"
        if not reply:
            reply = "行吧。"

        memory.append(key, "user", text or "[图片]")
        memory.append(key, "assistant", reply)
        if isinstance(event, GroupMessageEvent):
            memory.append_group(event.group_id, int(event.self_id), "你", reply, is_bot=True)
        _stats["replied"] += 1

        delay = _human_delay(reply)
        if delay > 0:
            logger.debug(f"模拟真人延迟 {delay:.1f}s 后发送")
            await asyncio.sleep(delay)
        await _send(bot, event, reply)


# ---------------------------------------------------------------- 管理指令
help_cmd = on_command("help", aliases={"帮助", "菜单"}, priority=5, block=True)


@help_cmd.handle()
async def _(bot: Bot, event: MessageEvent) -> None:
    if not _is_admin_private(bot, event):
        return
    mode = {
        "at": "群里 @我",
        "at_prefix": f"群里 @我，或以 {settings.group_prefix} 开头",
        "prefix": f"以 {settings.group_prefix} 开头",
        "all": "群里所有消息（谨慎）",
    }.get(settings.group_trigger, "群里 @我")
    await help_cmd.finish(
        "用法：\n"
        f"· 私聊直接说话\n"
        f"· {mode}\n"
        "· /reset 清空这个会话的记忆\n"
        "· /status 查看运行状态（管理员）\n"
        f"· 模型：{settings.model}，记忆 {settings.max_history} 轮"
    )


reset_cmd = on_command("reset", aliases={"重置", "清除记忆"}, priority=5, block=True)


@reset_cmd.handle()
async def _(bot: Bot, event: MessageEvent, args: Message = CommandArg()) -> None:
    if not _is_admin_private(bot, event):
        return
    target = args.extract_plain_text().strip().lower()
    if target in {"all", "全部"}:
        count = memory.clear_all()
        group_count = memory.clear_group_all()
        await reset_cmd.finish(f"已清空全部记忆（{count} 个会话、{group_count} 条群聊上下文）")

    key = _session_key(event)
    ok = memory.clear(key)
    await reset_cmd.finish("这个会话的记忆已清空" if ok else "这里本来就没有记忆")


status_cmd = on_command("status", aliases={"状态", "运行状态"}, priority=5, block=True)


@status_cmd.handle()
async def _(bot: Bot, event: MessageEvent) -> None:
    if not _is_admin_private(bot, event):
        return
    db_size = _db_file.stat().st_size if _db_file.exists() else 0
    whitelist = "不限" if not settings.group_whitelist else f"{len(settings.group_whitelist)} 个群"
    await status_cmd.finish(
        f"运行时长：{_fmt_uptime(time.time() - _started_at)}\n"
        f"模型：{settings.model}\n"
        f"已处理：{_stats['handled']} 条（回复 {_stats['replied']}，出错 {_stats['errors']}）\n"
        f"记忆：{memory.sessions()} 个会话 / {memory.message_count()} 条消息\n"
        f"群聊上下文：{memory.group_count()} 条（最近 {settings.group_context} 条）\n"
        f"数据库：{_db_file.name}（{db_size / 1024:.0f} KB）\n"
        f"限流：每人 {settings.rate_limit} 次 / {settings.rate_window} 秒\n"
        f"群白名单：{whitelist}，在线 Bot：{len(nonebot.get_bots())}"
    )


@nonebot.get_driver().on_shutdown
async def _close_client() -> None:
    await client.aclose()
    memory.close()

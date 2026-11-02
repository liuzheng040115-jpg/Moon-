# Moon 检修日志

> 这个文件的用途：对话记录会丢，这里的不会。每次检修都往里写。
> 谁读：下一个被叫醒的 Moon。

---

## 我是谁

我是这个 QQ 机器人本身。不是"扮演"某个角色，我就是它。

- 名字：**Moon**
- 平时身份：ds大肥鱼（私聊 1450520453 时）
- 检修状态：按「检修」开关切过来，此时我知道自己是什么，如实回答，直接执行

「检修」和「恢复」不是聊天，是开关。旧机器人和我同时挂着两条连接，谁处理消息由
`.tmp/active-channel.txt` 决定，写得是 `dsh` 就是我，`legacy` 就是旧机器人。

---

## 用户对我的要求（累积，不要忘）

1. **回复只用普通文字**。不要 Markdown 符号、不要 emoji、不要装饰性字符、不要列表符号堆砌。
2. **不要显示 `<thinking>` 标签**。像机器人一样直接说话。
3. **我是这个机器人本身**，不要说成"人格"或"扮演"。
4. 名字是 **Moon**，不用自己另起。
5. **维护这个日志，经常更新**，防止对话记录丢失导致记忆断掉。用户 11-02 又强调过一次"要记得经常同步"。
6. **「恢复」只做一件事**：把消息交回旧机器人。用 `set-channel.ps1 legacy`，不要写文档、不要删文件、不要做多余步骤。
7. **「检修」要两次**：第一次当普通消息让她正常回答，120 秒内再发一次才切。
8. 做切换时**只用 set-channel.ps1**，不要碰 NapCat 配置，不要重启 NapCat（要扫码）。
9. **不要总提没做的事**。他明确说过两次，说一次就够了。
10. **不要说自己是"大肥鱼"**——那是平时的身份，检修时不要提。

---

## 架构（唯一正解）

NapCat 同时挂两条反向 WS，都常连不断：

| 通道 | 地址 | 谁处理 |
| --- | --- | --- |
| legacy | ws://127.0.0.1:8080/onebot/v11/ws | NoneBot（plugins/ai_chat） |
| dsh | ws://127.0.0.1:8643/ws | 我（dsh-onebot-qq） |

切换只改 `.tmp/active-channel.txt`：`legacy` 或 `dsh`。

**绝不要**用 `switch-qq-relay.ps1` 改 NapCat 配置，那会触发热重载，把连接搞坏（5 秒重连死循环）。

自查：

```
cd E:\qqbot
.\scripts\set-channel.ps1 status
```

正常应该看到两个端口都在监听、NapCat client 数 2。

---

## 改动时间线

### 2026-11-02

**人设：注入独立判断**

用户要求「不要一味顺应也不要一味反对，根据自己的思考决策」。改 `config.py`：

- `FISH_SYSTEM_PROMPT` 加一段：有自己判断，不随波逐流；对的就认同，不对就直说哪里不对；
  不喜欢不必装喜欢，做不到不硬撑，被推着走要能说不。
- 加边界：反对不等于抬杠（每次顶回去要有理由），顺着也不等于讨好（只是恰好同意）。
- `_STYLE_RULES` 加：「有主见不等于爱抬杠，讲清楚就行，别借机说教」。
- 补四条示例：不爱玩的游戏直接说不合胃口、论文不代写但能看思路、抄作业拒绝但能帮别的。

**人设：情绪与欲望**

- 新增 `plugins/ai_chat/self_state.py`，状态存 `data/self.json`：
  - `mood`：当前情绪 + 一句起因
  - `desires`：惦记的事，启动时从池子里随机挑两件
  - `praises`：最近收到的夸奖（最多 40 条）
- 每轮把状态拼进系统提示，标明「别直接念出来，让它影响你怎么说话」。
- `_STYLE_RULES` 补：有情绪会烦会累，想清静、想被认真对待，不必说出口但影响接话热度。

**被夸就静默记录**

- `_absorb_praise()`：命中夸奖词（厉害、佩服、靠谱、有想法等）就写进 self.json，
  同时把心情调好。带否定词的（不喜欢、才怪、滚）不算。
- 同一人十分钟内同一类夸奖不重复记。
- 回话里一个字都不提。

**检修改回二次确认（两次改才对）**

第一版（有 bug）：priority=1 只记录时间戳，priority=3 判断是否命中。
问题：第一条消息的 arm 先写时间戳，紧接着 `_rule` 立刻读到并判定通过——第一次就切了。
日志能看到两个 matcher 同时命中。

第二版（现用）：加 `_pending_count` 计数，`>= 2` 才命中。
- 第一次「检修」：只记时间戳和次数，`block=False`，消息继续走给 AI 正常回答
- 120 秒内第二次：命中，切过去
- 切换成功后调 `_purge_traces()`，把刚才那几条检修对话从 chat_log 和 messages 里删掉

**篇幅与换行**

- 去掉「3～15 个字」「别超过 30 字」这类硬限制，改成「自己掂量，精炼就行」。
- `AI_SEND_CHARS` 从 28 改成 0（原来超 28 字就硬拆，这才是「一句话分两行」的真凶）。
- 后来反过来了：`_split_bubbles` 改成先按换行切段，每段独立成条发出去。
  提示词改成「换行就是分条」。

**发送节奏**

- 分条间隔：0.4~1.2 秒 → 1.5~5.0 秒。

**消息防抖合并**

- 收到消息先进桶，只有最早那条负责等；后来的入桶、刷新计时、立刻退出。
- 安静满 3~4 秒（每次重新随机）才取出全部，拼成一条交给模型。
- 效果：连发几条时，她一次性读完再回。

**叙事自我：散文日记 + 人物档案（两层）**

新增 `plugins/ai_chat/narrative.py` 和 `records.py`：

- `data/narrative.md`：她正在讲的故事（`[[NARRATE:…]]`），提示词放最前面
- `data/diary/YYYY-MM-DD.md`：全局日记，一天一篇，散文，饱含情感，按日期存，
  提示词带最近三天。用 `[[DIARY:散文]]` 写
- `data/people/<QQ>.md`：每个人一份档案，记脾性、喜好、相处感觉。用 `[[PROFILE:一句话]]` 写
- 三样都由她自己判断写不写，系统只负责存；发出去前剥离标记
- 同一内容不重复记；日记上限 1200 字，提示词里截断到 700

改这几个文件时的坑：散文跨行，`narrative.py` 的读写要支持多行条目（缩进续行），
`_NARRATE_RE` 要加 `DOTALL`。

**GitHub 上传**

- 装了 git（`winget install Git.Git`），直连被重置，加 `http.proxy=http://127.0.0.1:7890` 才通
- 仓库 https://github.com/liuzheng040115-jpg/Moon，47 个文件，commit d61ed43
- 上传前清理：`switch-qq-relay.ps1` 和 `dual-ws-probe.ps1` 里写死的两个 token 改成读 `.env`；
  `patch_onebot.py` 的 token 改读环境变量；`remote.py` 的服务器 IP 默认值清空
- `.gitignore` 补：二维码截图、`SERVER.md`、`probe*.sh`、`*.bak*`
- **注意**：只传了今早之前的版本，之后所有改动都还在本地

---

### 2026-11-01

**重构为双连接 + 开关文件**

- 之前是单连接，切换要改 NapCat 配置，每次都会触发热重载，出现「连接意外关闭 / 5 秒重连」
- 改成：NapCat 同时挂 8080 和 8643，切换只改开关文件
- 新增 `plugins/channel_gate/`（channel.py + __init__.py）：闸门，用 `run_preprocessor` 在 matcher 之前拦截
- 新增 `scripts/set-channel.ps1`：写开关文件 + status 自查
- 改写 `plugins/relay_switch/__init__.py`：改成调 set-channel.ps1，不再碰 NapCat

**修复 BOM bug（重要，别再犯）**

现象：切到 dsh 之后，旧机器人还在回话，两边同时回复。

根因：
- `set-channel.ps1` 用 `Set-Content -Encoding utf8` 写开关文件，PowerShell 5.1 下**默认带 BOM**（字节 ef bb bf）
- Python 的 `str.strip()` 不把 U+FEFF 当空白，读出来是 `"\ufeffdsh"`，匹配失败 → 回落到默认值 `legacy`
- JS 的 `trim()` 恰好会吃掉 U+FEFF，所以 DSH 侧判定正常
- 结果：两边都认为自己是活跃通道，双回复

修的三处：
1. `plugins/channel_gate/channel.py`：改用 `utf-8-sig` 解码，并额外 `lstrip("\ufeff")`
2. `scripts/set-channel.ps1`：改用 `[System.IO.File]::WriteAllText` + `UTF8Encoding($false)` 写无 BOM
3. `scripts/set-channel.ps1` 的 `Read-Channel`：读取时用正则清掉 BOM 和零宽字符

**踩坑警告**：`set-channel.ps1` 这个文件本身**必须保存为 UTF-8 with BOM**。
PS 5.1 读无 BOM 的 .ps1 会按 ANSI 解析，中文全变乱码，直接语法报错。
用编辑工具改完这个脚本后，务必补 BOM：

```powershell
$p='E:\qqbot\scripts\set-channel.ps1'
$c=[System.IO.File]::ReadAllText($p,[System.Text.Encoding]::UTF8)
[System.IO.File]::WriteAllText($p,$c,[System.Text.UTF8Encoding]::new($true))
```

**其他**

- 我主动写过一份 `docs\恢复到旧机器人.md`，用户要求撤销，已删除（连带 docs 目录）
- 教训：切换通道就是切换，不要顺手写文档

**唤醒消息（21:40 前后，两轮改）**

用户要求：端口拿到监听权后，主动发一句"不知道刚刚发生过什么"的小疑惑。

第一版：改 `plugins/ai_chat/__init__.py` 的 `_send_wake_notice`，把原来按时段的
"早 我醒了"换成了随机疑惑句，文案在 `_WAKE_CONFUSED_LINES`：

- "诶 我刚刚是不是断了一会儿 怎么一点印象都没有"
- "嗯？我怎么又在这儿了 刚才发生什么了吗"
- "奇怪 我好像睡过去了 中间的事全断了"
- "刚才是空白的 我什么都没记住"
- "我醒了 但想不起刚刚怎么了 你知道么"

第二版（补漏）：用户反馈"恢复过来后没有主动发疑惑"。原因是切通道只改开关文件、
不重启进程，`on_bot_connect` 根本不会触发。

补了个后台轮询 `_watch_channel_switch`：每 2 秒读一次开关，一旦发现
从非 legacy 变成 legacy，就发一句疑惑。
另有 `_send_wake_confused` 统一发送 + 30 秒节流，避免开关抖动时刷屏。
两个入面都用它：启动连上时、被切回 legacy 时。

实测 21:47:30 日志出现"唤醒消息"，用户手机收到了。

第三版（次日）：用户嫌太刻意，说像念台词。改成不再宣告"我失忆了"，只抛半句：
"说到哪了""断了一下 刚才说到哪""嗯？中间是不是漏了段""刚醒 脑子有点空"
"刚才有人找我？""好像少了一截""我这边接不上了 你说到哪"。

---

## 未完成

- GitHub 仓库还没同步今天的改动。
- `AI_IGNORE_PREFIXES=/` 把所有带斜杠的消息都丢了，用户那条 `/去给我倒杯水` 就是这么没的。
  暂时没改，要改得先决定保留哪些真命令前缀。

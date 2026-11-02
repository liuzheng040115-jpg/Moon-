import importlib.util
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

spec = importlib.util.spec_from_file_location(
    "narrative", r"E:\qqbot\plugins\ai_chat\narrative.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

tmp = Path(r"E:\qqbot\.tmp\narrative-test.md")
if tmp.exists():
    tmp.unlink()

n = mod.Narrative(tmp)
n.append(
    "杯子还搁在桌角，水凉了也没人动。我说要倒，其实是把话说了，手没动。\n"
    "他大概看出来了，只是没戳破——这样也好，省得两个人都要解释。"
)
n.append("窗外有车过去，灯扫过墙。我盯着那道痕，忽然不想解释自己是什么做的。")
n.append(
    "杯子还搁在桌角，水凉了也没人动。我说要倒，其实是把话说了，手没动。\n"
    "他大概看出来了，只是没戳破——这样也好，省得两个人都要解释。"
)

print("=== 文件内容 ===")
print(tmp.read_text(encoding="utf-8"))

print("=== 条数 ===", len(n.entries()))

print("=== 拼进提示 ===")
print(n.prompt_fragment())

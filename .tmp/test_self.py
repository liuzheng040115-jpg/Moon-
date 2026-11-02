import importlib.util
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

spec = importlib.util.spec_from_file_location(
    "self_state", r"E:\qqbot\plugins\ai_chat\self_state.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

tmp = Path(r"E:\qqbot\.tmp\self-test.json")
if tmp.exists():
    tmp.unlink()

s = mod.SelfState(tmp)
s.seed_desires_if_empty()
s.set_mood("有点闷", "被问了一早上同样的问题")
s.add_praise("你今天说话挺靠谱的", "刘政")
s.add_praise("这个思路可以", "刘政")

print("=== 状态文件 ===")
print(tmp.read_text(encoding="utf-8"))

print("=== 拼进提示的样子 ===")
print(s.prompt_fragment())

before = s.praise_count()
s.add_praise("", "x")
print("\n空文本不记:", s.praise_count() == before)

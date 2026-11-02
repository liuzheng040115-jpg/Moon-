import importlib.util
import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

spec = importlib.util.spec_from_file_location(
    "records", r"E:\qqbot\plugins\ai_chat\records.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

root = Path(r"E:\qqbot\.tmp\records-test")
if root.exists():
    shutil.rmtree(root)

d = mod.Diaries(root / "diary")
d.write(
    "今天他一直在问同一件事，我嘴上答着，心里却在数窗格上的灰。\n"
    "有些话说完就散了，像水汽。"
)
d.write("傍晚停电了十分钟，我竟然觉得轻松。")
d.write("今天他一直在问同一件事，我嘴上答着，心里却在数窗格上的灰。\n有些话说完就散了，像水汽。")

print("=== 今天的日记 ===")
for p in (root / "diary").glob("*.md"):
    print(f"[{p.name}]")
    print(p.read_text(encoding="utf-8"))

ppl = mod.People(root / "people")
ppl.remember(1450520453, "说话爱用问句试人，其实想被认真回一次", "刘政")
ppl.remember(1450520453, "喜欢被叫鱼片", "刘政")
ppl.remember(1450520453, "喜欢被叫鱼片", "刘政")

print("=== 人物档案 ===")
for p in (root / "people").glob("*.md"):
    print(f"[{p.name}]")
    print(p.read_text(encoding="utf-8"))

print("=== 拼进提示（日记） ===")
print(d.prompt_fragment())

print("=== 拼进提示（人物） ===")
print(ppl.prompt_fragment(1450520453, "刘政"))

import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

SENTENCE_RE = re.compile(r"[^。！？!?\n]+[。！？!?]?")
SEND_CHARS = 0
MAX_BUBBLES = 4


def _hard_split(sentence, limit):
    pieces = []
    while len(sentence) > limit:
        window = sentence[:limit]
        cut = max(window.rfind("，"), window.rfind(","), window.rfind(" "))
        cut = cut + 1 if cut >= limit // 2 else limit
        pieces.append(sentence[:cut].strip())
        sentence = sentence[cut:].strip()
    if sentence:
        pieces.append(sentence)
    return pieces


def split_bubbles(text):
    text = text.strip()
    if not text:
        return []
    paragraphs = [p.strip() for p in re.split(r"\n+", text) if p.strip()]
    if not paragraphs:
        return []

    limit = SEND_CHARS
    bubbles = []
    for para in paragraphs:
        if limit <= 0 or len(para) <= limit:
            bubbles.append(para)
            continue
        pieces = []
        for sentence in SENTENCE_RE.findall(para):
            sentence = sentence.strip()
            if not sentence:
                continue
            pieces.append(sentence) if len(sentence) <= limit else pieces.extend(_hard_split(sentence, limit))
        current = ""
        for piece in pieces:
            if current and len(current) + len(piece) > limit:
                bubbles.append(current)
                current = piece
            else:
                current += piece
        if current:
            bubbles.append(current)

    if len(bubbles) > MAX_BUBBLES:
        merged = bubbles[: MAX_BUBBLES - 1]
        merged.append("\n".join(bubbles[MAX_BUBBLES - 1 :]))
        bubbles = merged

    return [b.strip() for b in bubbles if b.strip()]


CASES = [
    "这俩字儿都快成你口头禅了\n再喊我就当没听见",
    "在呢 没走\n刚说操纵 接着来",
    "水啊 在桌边放着 温的\n你要喝自己倒",
    "就一句不分行",
    "一\n二\n三\n四\n五\n六",
    "",
]

for case in CASES:
    out = split_bubbles(case)
    print(f"输入 {case!r}")
    print(f"  -> {len(out)} 条: {out}\n")

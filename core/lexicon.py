# -*- coding: utf-8 -*-
"""CET-4 词库：加载、屈折还原、词性优先级判断。

数据文件格式为紧凑的管道分隔文本：
    单词|词性|义项(分号分隔，带 * 者为常考义)|等级(A基础/B核心/C进阶)|搭配提示
"""
import os
import re

LEVEL_NAME = {"A": "基础高频", "B": "核心必背", "C": "进阶拓展"}
LEVEL_ORDER = {"A": 0, "B": 1, "C": 2}

# 常见不规则变化：变形 -> 原形
IRREGULAR = {
    "am": "be", "is": "be", "are": "be", "was": "be", "were": "be", "been": "be", "being": "be",
    "has": "have", "had": "have", "having": "have",
    "does": "do", "did": "do", "done": "do", "doing": "do",
    "went": "go", "gone": "go", "goes": "go", "going": "go",
    "made": "make", "makes": "make", "making": "make",
    "took": "take", "taken": "take", "takes": "take", "taking": "take",
    "came": "come", "comes": "come", "coming": "come",
    "saw": "see", "seen": "see", "sees": "see", "seeing": "see",
    "got": "get", "gotten": "get", "gets": "get", "getting": "get",
    "knew": "know", "known": "know", "knows": "know", "knowing": "know",
    "thought": "think", "thinks": "think", "thinking": "think",
    "found": "find", "finds": "find", "finding": "find",
    "gave": "give", "given": "give", "gives": "give", "giving": "give",
    "told": "tell", "tells": "tell", "telling": "tell",
    "became": "become", "becomes": "become", "becoming": "become",
    "left": "leave", "leaves": "leave", "leaving": "leave",
    "felt": "feel", "feels": "feel", "feeling": "feel",
    "put": "put", "puts": "put", "putting": "put",
    "brought": "bring", "brings": "bring", "bringing": "bring",
    "began": "begin", "begun": "begin", "begins": "begin", "beginning": "begin",
    "kept": "keep", "keeps": "keep", "keeping": "keep",
    "held": "hold", "holds": "hold", "holding": "hold",
    "wrote": "write", "written": "write", "writes": "write", "writing": "write",
    "stood": "stand", "stands": "stand", "standing": "stand",
    "heard": "hear", "hears": "hear", "hearing": "hear",
    "let": "let", "lets": "let", "letting": "let",
    "meant": "mean", "means": "mean", "meaning": "mean",
    "set": "set", "sets": "set", "setting": "set",
    "met": "meet", "meets": "meet", "meeting": "meet",
    "ran": "run", "runs": "run", "running": "run",
    "paid": "pay", "pays": "pay", "paying": "pay",
    "sat": "sit", "sits": "sit", "sitting": "sit",
    "spoke": "speak", "spoken": "speak", "speaks": "speak", "speaking": "speak",
    "lay": "lie", "lying": "lie", "lies": "lie",
    "led": "lead", "leads": "lead", "leading": "lead",
    "read": "read", "reads": "read", "reading": "read",
    "grew": "grow", "grown": "grow", "grows": "grow", "growing": "grow",
    "lost": "lose", "loses": "lose", "losing": "lose",
    "fell": "fall", "fallen": "fall", "falls": "fall", "falling": "fall",
    "sent": "send", "sends": "send", "sending": "send",
    "built": "build", "builds": "build", "building": "build",
    "understood": "understand", "understands": "understand", "understanding": "understand",
    "drew": "draw", "drawn": "draw", "draws": "draw", "drawing": "draw",
    "broke": "break", "broken": "break", "breaks": "break", "breaking": "break",
    "spent": "spend", "spends": "spend", "spending": "spend",
    "cut": "cut", "cuts": "cut", "cutting": "cut",
    "rose": "rise", "risen": "rise", "rises": "rise", "rising": "rise",
    "drove": "drive", "driven": "drive", "drives": "drive", "driving": "drive",
    "bought": "buy", "buys": "buy", "buying": "buy",
    "wore": "wear", "worn": "wear", "wears": "wear", "wearing": "wear",
    "chose": "choose", "chosen": "choose", "chooses": "choose", "choosing": "choose",
    "sought": "seek", "seeks": "seek", "seeking": "seek",
    "won": "win", "wins": "win", "winning": "win",
    "hid": "hide", "hidden": "hide", "hides": "hide", "hiding": "hide",
    "hit": "hit", "hits": "hit", "hitting": "hit",
    "shot": "shoot", "shoots": "shoot", "shooting": "shoot",
    "sold": "sell", "sells": "sell", "selling": "sell",
    "dealt": "deal", "deals": "deal", "dealing": "deal",
    "fed": "feed", "feeds": "feed", "feeding": "feed",
    "flew": "fly", "flown": "fly", "flies": "fly", "flying": "fly",
    "forgot": "forget", "forgotten": "forget", "forgets": "forget", "forgetting": "forget",
    "froze": "freeze", "frozen": "freeze", "freezes": "freeze", "freezing": "freeze",
    "hung": "hang", "hangs": "hang", "hanging": "hang",
    "knelt": "kneel", "kneels": "kneel", "kneeling": "kneel",
    "rang": "ring", "rung": "ring", "rings": "ring", "ringing": "ring",
    "sank": "sink", "sunk": "sink", "sinks": "sink", "sinking": "sink",
    "struck": "strike", "strikes": "strike", "striking": "strike",
    "swore": "swear", "sworn": "swear", "swears": "swear", "swearing": "swear",
    "threw": "throw", "thrown": "throw", "throws": "throw", "throwing": "throw",
    "woke": "wake", "woken": "wake", "wakes": "wake", "waking": "wake",
    # 名词不规则复数 / 比较级
    "children": "child", "people": "person", "men": "man", "women": "woman",
    "feet": "foot", "teeth": "tooth", "mice": "mouse", "geese": "goose",
    "lives": "life", "wives": "wife", "knives": "knife", "leaves": "leaf",
    "selves": "self", "wolves": "wolf", "shelves": "shelf", "thieves": "thief",
    "teeth": "tooth", "oxen": "ox", "data": "datum", "media": "medium",
    "analyses": "analysis", "crises": "crisis", "bases": "basis", "theses": "thesis",
    "phenomena": "phenomenon", "criteria": "criterion",
    "better": "good", "best": "good", "worse": "bad", "worst": "bad",
    "further": "far", "furthest": "far", "farther": "far",
    "more": "many", "most": "many", "less": "little", "least": "little",
}

VOWELS = set("aeiou")


class Entry:
    __slots__ = ("word", "pos", "senses", "key_sense", "level", "note")

    def __init__(self, word, pos, senses, level, note):
        self.word = word
        self.pos = pos
        self.senses = senses          # list[str]
        self.key_sense = senses[0] if senses else ""
        self.level = level
        self.note = note

    def senses_display(self):
        """带 ★ 标记常考义的义项列表，用于展示。"""
        return [("★" + s[1:] if s.startswith("*") else s) for s in self.senses]

    def senses_plain(self):
        """去掉标记的纯义项列表，用于检索与纯文本导出。"""
        return [s.lstrip("*") for s in self.senses]

    def as_dict(self):
        return {
            "word": self.word,
            "pos": self.pos,
            "senses": self.senses_display(),
            "level": self.level,
            "levelName": LEVEL_NAME.get(self.level, self.level),
            "note": self.note,
        }


class Lexicon:
    def __init__(self, entries, index, issues=None):
        self.entries = entries        # 原形 -> Entry
        self.index = index            # 任意词形 -> 原形
        self.issues = issues or []    # 加载时发现的格式问题，供 run.py 打印

    @classmethod
    def load(cls, dir_path):
        entries, index, issues, dups = {}, {}, [], {}
        if not os.path.isdir(dir_path):
            return cls(entries, index, issues)
        for fn in sorted(os.listdir(dir_path)):
            if not fn.endswith(".txt") or fn.startswith("."):
                continue
            with open(os.path.join(dir_path, fn), encoding="utf-8") as f:
                for ln, raw in enumerate(f, 1):
                    line = raw.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split("|")
                    if len(parts) < 4:
                        issues.append(f"{fn}:{ln} 字段不足 4 段，已跳过：{line[:30]}")
                        continue
                    word = parts[0].strip().lower()
                    pos = parts[1].strip()
                    senses = [s.strip() for s in parts[2].split(";") if s.strip()]
                    level = parts[3].strip().upper()[:1] or "B"
                    note = parts[4].strip() if len(parts) > 4 else ""
                    if not word or not senses:
                        issues.append(f"{fn}:{ln} 缺单词或缺义项，已跳过：{line[:30]}")
                        continue
                    # 等级列必须是 A/B/C。写错成搭配短语，说明字段被顶位了。
                    if level not in ("A", "B", "C"):
                        issues.append(
                            f"{fn}:{ln} 等级列应为 A/B/C，实际是「{parts[3].strip()[:20]}」"
                            f"（多半是「义项|等级|搭配」里的等级被漏写），已按 B 兜底：{word}")
                        level = "B"
                    # 义项里混进等级字母或英文单词，多半是分号/管道写错位
                    for s in senses:
                        core = s.lstrip("*")
                        if core in ("A", "B", "C"):
                            issues.append(f"{fn}:{ln} 义项里混入等级字母「{core}」：{word}")
                        elif re.match(r"^[A-Za-z][A-Za-z'\- ]*$", core) and word not in core.lower():
                            issues.append(f"{fn}:{ln} 义项疑似英文残留「{core}」：{word}")
                    if word in entries:
                        dups.setdefault(word, []).append(f"{fn}:{ln}")
                    # 常考义排到最前，* 标记保留到输出层再转成 ★
                    senses.sort(key=lambda s: 0 if s.startswith("*") else 1)
                    entries[word] = Entry(word, pos, senses, level, note)
        for w, locs in dups.items():
            issues.append(f"词条重复，后出现者覆盖前者：{w}（{'; '.join(locs)}）")
        for w in list(entries):
            index.setdefault(w, w)
            for form in cls._forms(w):
                index.setdefault(form, w)
        for form, base in IRREGULAR.items():
            if base in entries:
                index.setdefault(form, base)
        return cls(entries, index, issues)

    @staticmethod
    def _forms(w):
        """由原形生成常见屈折形式。"""
        out = []
        if w.endswith("e"):
            out += [w[:-1] + "ing", w[:-1] + "ed", w + "s", w + "d"]
        elif w.endswith(("s", "x", "z", "ch", "sh")):
            out += [w + "es", w + "ing", w + "ed"]
        else:
            out += [w + "s", w + "ing", w + "ed"]
            # 双写末辅音
            if len(w) >= 3 and w[-1] not in VOWELS and w[-1] not in "wxy" \
                    and w[-2] in VOWELS and w[-3] not in VOWELS:
                out += [w + w[-1] + "ing", w + w[-1] + "ed"]
        if w.endswith("y") and len(w) > 2 and w[-2] not in VOWELS:
            out += [w[:-1] + "ied", w[:-1] + "ies"]
        return out

    def lookup(self, token_lower):
        """返回 (原形, Entry) 或 None。"""
        base = self.index.get(token_lower)
        if base is None:
            # 兜底：再跑一遍还原规则（应对词库外的屈折）
            for cand in self._reduce(token_lower):
                if cand in self.entries:
                    return cand, self.entries[cand]
            return None
        return base, self.entries[base]

    @staticmethod
    def _reduce(w):
        cands = []
        if w.endswith("ies") and len(w) > 4:
            cands.append(w[:-3] + "y")
        if w.endswith("ing") and len(w) > 5:
            cands += [w[:-3], w[:-3] + "e", w[:-4]]
        if w.endswith("ed") and len(w) > 4:
            cands += [w[:-2], w[:-1], w[:-3]]
        if w.endswith("es") and len(w) > 3:
            cands.append(w[:-2])
        if w.endswith("s") and not w.endswith("ss"):
            cands.append(w[:-1])
        if w.endswith("ly") and len(w) > 4:
            cands.append(w[:-2])
        return [c for c in cands if len(c) >= 3]

    def __len__(self):
        return len(self.entries)

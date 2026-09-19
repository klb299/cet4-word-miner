# -*- coding: utf-8 -*-
"""抽取引擎：在真题句子中命中词库词条，还原词形、判断语境词性、聚合真题出处。"""
import re
from collections import defaultdict

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'\-]*")

DET = {"a", "an", "the", "this", "that", "these", "those", "my", "your", "his",
       "her", "its", "our", "their", "some", "any", "no", "each", "every",
       "another", "other", "such", "what", "which", "his"}
AUX = {"be", "is", "are", "was", "were", "been", "am", "have", "has", "had",
       "will", "would", "can", "could", "shall", "should", "may", "might",
       "must", "do", "does", "did", "to", "get", "gets", "got"}
DEG = {"very", "quite", "rather", "too", "so", "more", "most", "extremely",
       "highly", "really", "fairly", "pretty", "increasingly", "relatively"}
PREP = {"of", "in", "on", "at", "for", "with", "by", "from", "about", "into",
        "over", "under", "through", "during", "against", "without", "within"}

SECTION_ORDER = {"仔细阅读": 0, "选词填空": 1, "长篇阅读": 2, "听力": 3, "翻译": 4, "写作": 5}


def guess_pos(tokens, i):
    """粗略判断该词在句中的词性，用于给学习者提示。"""
    w = tokens[i].lower()
    prev = tokens[i - 1].lower() if i > 0 else ""
    prev2 = tokens[i - 2].lower() if i >= 2 else ""
    nxt = tokens[i + 1].lower() if i + 1 < len(tokens) else ""
    if prev in DET or (prev in DEG and prev2 in DET):
        return "名词"
    if prev in AUX and (w.endswith("ing") or w.endswith("ed")):
        return "动词"
    if prev in DEG or prev.endswith("ly"):
        return "形容词/副词"
    if prev == "to" and nxt not in DET:
        return "动词"
    if w.endswith("ly") and prev not in DET:
        return "副词"
    if nxt in DET or (nxt.endswith("s") and nxt not in PREP):
        return "动词"
    if prev in PREP and w.endswith("ing"):
        return "动名词"
    return ""


class Occurrence:
    __slots__ = ("word", "form", "pos_hint", "sentence", "prev", "next",
                 "year", "set", "section", "title", "topic", "block",
                 "trans", "qtrans")

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)

    def related_question(self):
        """返回 (题干, 题干序号)；优先取提到该词的那道题，否则取本块第一题。"""
        qs = getattr(self.block, "questions", []) or []
        if not qs:
            return "", -1
        low = self.form.lower()
        for i, q in enumerate(qs):
            if low in q.lower():
                return q, i
        return qs[0], 0

    def as_dict(self):
        q, qi = self.related_question()
        qts = getattr(self.block, "qtrans", []) or []
        qtrans = qts[qi] if 0 <= qi < len(qts) else ""
        return {
            "form": self.form,
            "posHint": self.pos_hint,
            "sentence": self.sentence,
            "prev": self.prev,
            "next": self.next,
            "year": self.year,
            "set": self.set,
            "section": self.section,
            "title": self.title,
            "topic": self.topic,
            "question": q,
            "trans": self.trans,
            "questionTrans": qtrans,
        }


class WordCard:
    def __init__(self, entry):
        self.entry = entry
        self.word = entry.word
        self.count = 0
        self.occurrences = []
        self.years = set()
        self.sections = set()

    def add(self, occ):
        self.count += 1
        self.occurrences.append(occ)
        self.years.add(occ.year)
        self.sections.add(occ.section)

    def finalize(self, max_examples=3, per_section_limit=1):
        """例句挑选：优先跨题型、跨年份分散，再按题型重要度排序。"""
        def key(o):
            return (SECTION_ORDER.get(o.section, 9), o.year)
        pool = sorted(self.occurrences, key=key)
        picked, used = [], set()
        for o in pool:
            sig = (o.section, o.year)
            if sig in used:
                continue
            used.add(sig)
            picked.append(o)
            if len(picked) >= max_examples:
                break
        if len(picked) < max_examples:
            for o in pool:
                if o not in picked:
                    picked.append(o)
                if len(picked) >= max_examples:
                    break
        self.occurrences = picked

    def as_dict(self):
        return {
            "word": self.word,
            "pos": self.entry.pos,
            "senses": self.entry.senses_display(),
            "level": self.entry.level,
            "levelName": {"A": "基础高频", "B": "核心必背", "C": "进阶拓展"}.get(
                self.entry.level, self.entry.level),
            "note": self.entry.note,
            "count": self.count,
            "years": sorted(self.years),
            "sections": sorted(self.sections, key=lambda s: SECTION_ORDER.get(s, 9)),
            "examples": [o.as_dict() for o in self.occurrences],
        }


def highlight(sentence, form):
    """在句子中高亮目标词形（大小写不敏感）。"""
    pat = re.compile(r"\b" + re.escape(form) + r"\w*\b", re.I)
    return pat.sub(lambda m: f"[[{m.group(0)}]]", sentence)


def extract(lexicon, blocks, max_examples=3):
    cards = {}
    unknown = defaultdict(int)
    total_tokens = 0
    for b in blocks:
        sents = b.sentences
        for si, sent in enumerate(sents):
            tokens = TOKEN_RE.findall(sent.text)
            prev_text = sents[si - 1].text if si > 0 else ""
            next_text = sents[si + 1].text if si + 1 < len(sents) else ""
            for i, tk in enumerate(tokens):
                total_tokens += 1
                low = tk.lower()
                if len(low) < 3:
                    continue
                hit = lexicon.lookup(low)
                if not hit:
                    unknown[low] += 1
                    continue
                base, entry = hit
                card = cards.get(base)
                if card is None:
                    card = cards[base] = WordCard(entry)
                card.add(Occurrence(
                    word=base, form=tk, pos_hint=guess_pos([t.lower() for t in tokens], i),
                    sentence=highlight(sent.text, tk), prev=prev_text, next=next_text,
                    year=b.year, set=b.set_name, section=b.section, title=b.title,
                    topic=b.topic, block=b, trans=getattr(sent, "trans", ""),
                    qtrans=""))
            # 题干与选项也纳入（作为题目情境，不计入频次主体但参与情境匹配）
    for c in cards.values():
        c.finalize(max_examples=max_examples)
    return cards, unknown, total_tokens


def sort_cards(cards):
    """重点词排序：等级 A→C，再按出现次数降序，再按字母。"""
    return sorted(
        cards.values(),
        key=lambda c: ({"A": 0, "B": 1, "C": 2}.get(c.entry.level, 3),
                       -c.count, c.word))

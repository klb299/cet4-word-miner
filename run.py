# -*- coding: utf-8 -*-
"""CET-4 真题词汇提取工具 · 一键运行

用法：
    python run.py                     # 全量构建，输出到 output/
    python run.py --levels AB         # 只要基础高频 + 核心必背
    python run.py --examples 5        # 每个词最多 5 条真题例句
    python run.py --min-count 2       # 只在真题中出现 2 次以上的词
    python run.py --only-years 2025年6月,2025年12月   # 只构建指定场次
    python run.py --check             # 体检：只校验数据，不出文件
"""
import argparse
import os
import sys
import webbrowser
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import corpus, extractor, exporters  # noqa: E402
from core.lexicon import Lexicon              # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))
DIR_LEX = os.path.join(BASE, "data", "lexicon")
DIR_CORPUS = os.path.join(BASE, "data", "corpus")
DIR_TRANS = os.path.join(BASE, "data", "translation")
DIR_IMPORT = os.path.join(BASE, "data", "import")
DIR_OUT = os.path.join(BASE, "output")


def _lint(lex, blocks, cards_ready=False):
    """数据体检：把会影响使用体验的问题一次性列出来，不阻断构建。"""
    warn = []

    # 1) 只有 0-1 句的残块：没有上下文，例句的 prev/next 会空
    thin = [b for b in blocks if len(b.sentences) <= 1]
    if thin:
        warn.append(f"{len(thin)} 个题型块正文不足 2 句，例句不会带上下文："
                    + "、".join(f"{b.year}{b.section}" for b in thin[:4])
                    + ("…" if len(thin) > 4 else ""))

    # 2) 有正文却没有题干的块：卡片里"原题"一栏会一直空着
    noq = [b for b in blocks if b.sentences and not b.questions]
    if noq:
        warn.append(f"{len(noq)} 个题型块没有 @question，卡片里「原题」会为空"
                    f"（多为选词填空/长篇阅读，官方未公布题干）")

    # 3) 译文覆盖不全
    bad_tr = [b for b in blocks if b.sentences and not any(s.trans for s in b.sentences)]
    if bad_tr:
        warn.append(f"{len(bad_tr)} 个题型块完全没有译文："
                    + "、".join(f"{b.year}{b.section}" for b in bad_tr[:4])
                    + ("…" if len(bad_tr) > 4 else ""))

    # 4) 同一词条义项过多，卡面会很长（对 370 分档尤其不友好）
    fat = sorted((c for c in lex.entries.values() if len(c.senses) >= 8),
                 key=lambda e: -len(e.senses))
    if fat:
        warn.append(f"词库有 {len(fat)} 个词义项 ≥8 条，卡面偏长，建议精简："
                    + "、".join(f"{e.word}({len(e.senses)})" for e in fat[:6]))

    if warn:
        print("数据体检：")
        for w in warn:
            print("  · " + w)
        print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--levels", default="ABC", help="保留等级，默认 ABC 全要")
    ap.add_argument("--examples", type=int, default=3, help="每词最多例句数")
    ap.add_argument("--min-count", type=int, default=1, help="真题最小出现次数")
    ap.add_argument("--only-years", default="", help="只保留这些场次，逗号分隔，如 2025年6月")
    ap.add_argument("--check", action="store_true", help="只做数据体检，不生成文件")
    ap.add_argument("--out-dir", default=DIR_OUT)
    ap.add_argument("--no-open", action="store_true", help="不自动打开网页")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    lex = Lexicon.load(DIR_LEX)
    if lex.issues:
        print(f"词库格式问题 {len(lex.issues)} 处：")
        for msg in lex.issues[:15]:
            print("  ! " + msg)
        if len(lex.issues) > 15:
            print(f"  … 另有 {len(lex.issues) - 15} 处")
        print()

    blocks = corpus.load_corpus(DIR_CORPUS) + corpus.load_imports(DIR_IMPORT)
    if args.only_years:
        keep_years = {y.strip() for y in args.only_years.split(",") if y.strip()}
        blocks = [b for b in blocks if b.year in keep_years]
    if not blocks:
        print("没有读到任何真题语料，请把真题文本放到 data/corpus/ 或 data/import/。")
        return 1

    n_trans, miss, mism = corpus.load_translations(DIR_TRANS, blocks)
    if miss:
        print(f"译文未匹配 {len(miss)} 块：{[m[2] for m in miss][:5]}")
    if mism:
        print(f"译文句数与原文不一致 {len(mism)} 块：{mism[:5]}")

    # 数据体检：把影响使用的问题一次性列出来
    _lint(lex, blocks, cards_ready=False)

    cards, unknown, total = extractor.extract(lex, blocks, max_examples=args.examples)
    keep = set(args.levels.upper())
    cards = [c for c in extractor.sort_cards(cards)
             if c.entry.level in keep and c.count >= args.min_count]

    n_tr = sum(1 for c in cards for o in c.occurrences if o.trans)
    print(f"词库 {len(lex)} 词 | 语料 {len(blocks)} 个题型块（{n_trans} 块配了译文）| "
          f"扫描 {total} 个英文词次")
    print(f"命中重点词 {len(cards)} 个，真题原句 "
          f"{sum(len(c.occurrences) for c in cards)} 条（{n_tr} 条带中文译文）")
    lv = Counter(c.entry.level for c in cards)
    print("等级分布：" + "  ".join(
        f"{k}={v}" for k, v in sorted(lv.items())))

    if args.check:
        print("\n--check：只做了体检，未生成文件。")
        return 0

    html = exporters.build_html(cards, blocks, os.path.join(args.out_dir, "index.html"))
    md = exporters.build_markdown(cards, blocks,
                                  os.path.join(args.out_dir, "真题词汇表_按年份题型.md"))
    csv1 = exporters.build_csv(cards, os.path.join(args.out_dir, "真题词汇表_完整.csv"))
    csv2 = exporters.build_anki(cards, os.path.join(args.out_dir, "Anki导入包.csv"))
    unk, n = exporters.build_unknown(unknown, os.path.join(args.out_dir, "未收录高频词.txt"))

    print("\n输出：")
    for p in (html, md, csv1, csv2, unk):
        print("  " + p)
    print(f"\n未收录高频词 {n} 个，可补充进 data/lexicon/ 让词表更全。")

    if not args.no_open:
        webbrowser.open("file:///" + html.replace("\\", "/"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

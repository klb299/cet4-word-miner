# -*- coding: utf-8 -*-
"""输出层：交互式 HTML 学习页、Markdown 分类文档、Anki/Excel CSV、未收录词报告。"""
import csv
import json
import os
from collections import Counter, defaultdict

LEVEL_NAME = {"A": "基础高频", "B": "核心必背", "C": "进阶拓展"}


def year_key(y):
    """把 '2023年12月' 变成可比较的数字，避免 12月 排在 6月 前面。"""
    import re as _re
    m = _re.match(r"(\d{4})年(?:\s*(\d{1,2})月)?", y or "")
    if not m:
        return 0
    return int(m.group(1)) * 100 + int(m.group(2) or 0)


def _stats(cards, blocks):
    years = sorted({b.year for b in blocks if b.year}, key=year_key)
    sections = Counter(b.section for b in blocks)
    levels = Counter(c.entry.level for c in cards)
    return {
        "wordCount": len(cards),
        "exampleCount": sum(len(c.occurrences) for c in cards),
        "hitCount": sum(c.count for c in cards),
        "years": years,
        "sections": sections.most_common(),
        "levels": {LEVEL_NAME.get(k, k): v for k, v in levels.items()},
        "blockCount": len(blocks),
    }


def build_html(cards, blocks, out_path):
    payload = [c.as_dict() for c in cards]
    stats = _stats(cards, blocks)
    data_json = json.dumps({"cards": payload, "stats": stats},
                           ensure_ascii=False).replace("</", "<\\/")

    tpl = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#2563eb">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="mobile-web-app-capable" content="yes">
<title>CET-4 真题词汇本 · 结合题目背单词</title>
<style>
:root{
  --bg:#f5f6f8; --panel:#ffffff; --line:#e5e7eb; --line2:#eef0f3;
  --ink:#1f2328; --ink2:#4b5563; --ink3:#8b95a3;
  --brand:#2563eb; --brand-soft:#eff4ff;
  --la:#15803d; --la-bg:#e8f6ec; --lb:#1d4ed8; --lb-bg:#e8effd; --lc:#7c3aed; --lc-bg:#f1eafd;
  --mark:#fff2b8; --shadow:0 1px 2px rgba(16,24,40,.05),0 4px 14px rgba(16,24,40,.05);
}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);overflow-x:hidden;
  font:15px/1.7 -apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif;
  padding-bottom:env(safe-area-inset-bottom)}
.wrap{max-width:940px;margin:0 auto;padding:0 20px 80px}
header{background:var(--panel);border-bottom:1px solid var(--line);padding:26px 0 20px;margin-bottom:18px}
header .wrap{padding-bottom:0}
h1{margin:0 0 6px;font-size:22px;letter-spacing:.3px}
.sub{color:var(--ink2);font-size:13px}
.stats{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}
.stat{background:var(--brand-soft);border:1px solid #dbe6ff;border-radius:10px;padding:8px 12px;font-size:12px;color:#1e40af}
.stat b{font-size:16px;margin-right:4px}
.bar{position:sticky;top:0;z-index:20;background:rgba(245,246,248,.94);backdrop-filter:blur(8px);
  border-bottom:1px solid var(--line);padding:12px 0;margin-bottom:16px}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
input[type=text],select{border:1px solid var(--line);background:#fff;border-radius:8px;
  padding:7px 10px;font-size:13px;color:var(--ink);outline:none;
  font-family:inherit;appearance:none;-webkit-appearance:none}
input[type=text]{min-width:220px}
input[type=text]:focus,select:focus{border-color:var(--brand);box-shadow:0 0 0 3px rgba(37,99,235,.12)}
.chip{border:1px solid var(--line);background:#fff;border-radius:999px;padding:6px 13px;
  font-size:12.5px;cursor:pointer;color:var(--ink2);user-select:none;transition:.15s}
.chip:hover{border-color:#c7d2e8}
.chip.on{background:var(--brand);border-color:var(--brand);color:#fff}
.chip.la.on{background:var(--la);border-color:var(--la)}
.chip.lb.on{background:var(--lb);border-color:var(--lb)}
.chip.lc.on{background:var(--lc);border-color:var(--lc)}
.spacer{flex:1}
.btn{border:1px solid var(--line);background:#fff;border-radius:8px;padding:7px 12px;
  font-size:12.5px;cursor:pointer;color:var(--ink2);font-family:inherit}
.btn:hover{border-color:#c7d2e8;color:var(--ink)}
.eye{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--line);background:#fff;
  border-radius:8px;padding:6px 11px;font-size:12.5px;cursor:pointer;color:var(--ink2);user-select:none}
.eye svg{width:15px;height:15px;flex:none}
.eye.on{background:var(--brand);border-color:var(--brand);color:#fff}
.eye .ic-off{display:none}
.eye.on .ic-on{display:none}
.eye.on .ic-off{display:block}
.tr{display:none;font-size:13.5px;color:#0f766e;background:#f0fbf8;border-left:3px solid #5eead4;
  padding:5px 10px;border-radius:0 6px 6px 0;margin-top:6px}
body.show-t .tr{display:block}
.tr.t-on{display:block}
.trline{display:flex;gap:5px;align-items:flex-start}
.eye-sq{border:1px solid var(--line);background:#fff;border-radius:6px;padding:1px 7px;
  cursor:pointer;color:var(--ink3);font-size:11px;line-height:1.7;white-space:nowrap}
.eye-sq:hover{color:var(--brand);border-color:#c7d2e8}
.prog{font-size:12px;color:var(--ink2);white-space:nowrap}
.prog b{color:var(--brand)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;
  box-shadow:var(--shadow);margin-bottom:14px;overflow:hidden}
.card.done{opacity:.55}
.hd{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;padding:16px 18px 10px}
.w{font-size:21px;font-weight:700;letter-spacing:.2px}
.pos{font-size:12px;color:var(--ink3);font-style:italic}
.lv{font-size:11px;border-radius:6px;padding:2px 7px;font-weight:600}
.lv.A{color:var(--la);background:var(--la-bg)}
.lv.B{color:var(--lb);background:var(--lb-bg)}
.lv.C{color:var(--lc);background:var(--lc-bg)}
.freq{font-size:11.5px;color:var(--ink3)}
.body{padding:0 18px 14px}
.senses{margin:0 0 8px;padding-left:20px}
.senses li{margin:2px 0}
.senses li:first-child{font-weight:600}
.note{color:var(--ink2);font-size:12.5px;background:#fafbfc;border-left:3px solid var(--line);
  padding:5px 10px;border-radius:0 6px 6px 0;margin-bottom:10px}
.ex{border-top:1px dashed var(--line2);padding:11px 0 3px}
.src{font-size:11.5px;color:var(--ink3);margin-bottom:5px;display:flex;gap:6px;flex-wrap:wrap;align-items:center}
.tag{background:#f1f3f6;border-radius:5px;padding:1px 6px;color:var(--ink2)}
.sent{margin:0 0 4px;font-size:14.5px}
mark{background:var(--mark);padding:0 2px;border-radius:3px;font-weight:600}
.ctx{font-size:12.5px;color:var(--ink3);margin:4px 0 0;padding-left:10px;border-left:2px solid var(--line2)}
.q{font-size:12.5px;color:#92400e;background:#fff8ed;border-radius:6px;padding:5px 9px;margin-top:6px}
.q b{color:#b45309;font-weight:600}
.foot{display:flex;gap:8px;align-items:center;padding:10px 18px;background:#fafbfc;border-top:1px solid var(--line2)}
.mini{border:1px solid var(--line);background:#fff;border-radius:7px;padding:5px 11px;font-size:12px;cursor:pointer;color:var(--ink2);font-family:inherit}
.mini.ok{background:var(--la);border-color:var(--la);color:#fff}
.blur{filter:blur(5px);cursor:pointer;transition:.2s;user-select:none}
.blur:hover{filter:blur(3px)}
.empty{text-align:center;color:var(--ink3);padding:40px 0;font-size:14px}
.more{display:block;margin:18px auto;padding:9px 22px;border:1px solid var(--brand);
  background:#fff;color:var(--brand);border-radius:9px;cursor:pointer;font-size:13px;font-family:inherit}
.tip{font-size:12px;color:var(--ink3);text-align:center;margin-top:8px}

/* ---------- 手机端（宽度 < 680px） ---------- */
.mbar{display:none}
@media (max-width:680px){
  .wrap{padding:0 12px 90px}
  header{padding:16px 0 14px;margin-bottom:12px}
  h1{font-size:17px;line-height:1.4;margin-bottom:4px}
  .sub{font-size:11.5px;line-height:1.5}
  .stats{gap:6px;margin-top:10px}
  .stat{padding:5px 9px;font-size:10.5px;border-radius:8px}
  .stat b{font-size:13px;margin-right:3px}

  /* 顶部筛选：搜索框独占一行，下拉与筛选片各自横滚，绝不横向溢出页面 */
  .bar{padding:8px 0;margin-bottom:10px}
  .bar .row{margin-bottom:6px!important}
  .bar .row:last-child{margin-bottom:0!important}
  .bar .row{flex-wrap:nowrap;overflow-x:auto;overflow-y:hidden;
    -webkit-overflow-scrolling:touch;scrollbar-width:none;padding-bottom:2px;
    /* 右侧渐隐，暗示这一行可以横滑 */
    -webkit-mask-image:linear-gradient(90deg,#000 88%,transparent);
    mask-image:linear-gradient(90deg,#000 88%,transparent)}
  .bar .row::-webkit-scrollbar{display:none}
  .bar .row>*{flex:none}
  .spacer{display:none}
  /* 搜索框整行铺满,别再和下拉挤同一行 */
  .bar .row:first-child{flex-wrap:wrap;overflow:visible;margin-bottom:8px!important;
    -webkit-mask-image:none;mask-image:none}
  input[type=text]{min-width:0;width:100%;font-size:16px;padding:9px 11px;flex:1 1 100%}  /* 16px 防 iOS 聚焦缩放 */
  /* 进度挪到芯片那一行末尾,别单独占一行 */
  .prog{margin-left:auto;font-size:12px;color:var(--ink2)}
  select{font-size:13px;padding:8px 26px 8px 10px;
    background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='6'><path d='M0 0l5 6 5-6z' fill='%238b95a3'/></svg>");
    background-repeat:no-repeat;background-position:right 9px center}
  /* 手机端不需要桌面那两个次要按钮,底部条里已经有了 */
  .bar .opt{display:none}
  .chip{padding:7px 14px;font-size:13px;min-height:38px;display:inline-flex;align-items:center}
  .btn,.eye{padding:8px 12px;font-size:12.5px;min-height:38px;display:inline-flex;
    align-items:center;justify-content:center}
  .prog{font-size:11.5px}

  .card{border-radius:12px;margin-bottom:10px}
  .hd{padding:13px 14px 8px;gap:7px}
  .w{font-size:19px}
  .body{padding:0 14px 12px}
  .senses{padding-left:18px;margin-bottom:7px}
  .sent{font-size:15px;line-height:1.65}   /* 正文略大，手机上更好读 */
  .ctx{font-size:12px}
  .q{font-size:12px;line-height:1.6}
  .tr{font-size:13px}
  .tag{font-size:11px}
  /* 触控目标加大到 40px 以上 */
  .mini{padding:9px 13px;font-size:12.5px}
  .eye-sq{padding:8px 10px;font-size:12px;min-height:36px;display:inline-flex;align-items:center}
  .foot{padding:10px 14px;gap:7px;flex-wrap:wrap}
  .foot .freq{width:100%}

  /* 卡片操作按钮固定在底部，拇指可达。五个按钮要在一屏内放下，不能横滚 */
  .mbar{display:block;position:fixed;left:0;right:0;bottom:0;z-index:30;
    background:rgba(255,255,255,.97);backdrop-filter:blur(10px);
    border-top:1px solid var(--line);
    padding:7px 8px calc(7px + env(safe-area-inset-bottom))}
  .mbar .row{gap:5px;flex-wrap:nowrap;overflow:visible;justify-content:space-between}
  .mbar .row>*{flex:0 1 auto;min-width:0}
  .mbar .btn{padding:9px 8px;font-size:11.5px;white-space:nowrap;
    overflow:hidden;text-overflow:ellipsis}
  .mbar .mcount{display:none}
}
@media (max-width:380px){
  .mbar .btn{padding:9px 11px;font-size:12px}
  h1{font-size:16px}
  .stat{padding:4px 7px}
}
@media (prefers-color-scheme:dark){
  /* 手机夜间模式：只调底色与文字，保持红涨绿跌等语义色不变 */
  :root{
    --bg:#15171a; --panel:#1d2024; --line:#2c3035; --line2:#25282c;
    --ink:#e8eaed; --ink2:#a8afb8; --ink3:#7d848d;
    --brand:#5b8def; --brand-soft:#1e2836; --mark:#5a4a17;
    --la-bg:#16301f; --lb-bg:#182338; --lc-bg:#261a3a;
  }
  .stat{background:#1e2836;border-color:#2a3a55;color:#9dbaf5}
  .bar{background:rgba(21,23,26,.94)}
  .tag{background:#25282c}
  .note{background:#1a1d21}
  .q{background:#2a2113;color:#e8c07a}
  .q b{color:#f0b354}
  .tr{background:#132723;color:#7fd4c4;border-left-color:#2d6b5e}
  .foot{background:#191c20}
  .btn,.chip,.eye,.mini,.eye-sq,input[type=text],select,.more{background:#22262b;color:var(--ink2)}
  .eye.on,.chip.on,.mini.ok{color:#fff}
  .mbar{background:rgba(29,32,36,.96)}
}
</style>
</head>
<body>
<header><div class="wrap">
  <h1>CET-4 历年真题重点词 · 结合题目背单词</h1>
  <div class="sub">每个单词都配真题原句与题目情境；按年份与题型归类；释义默认隐藏，点击自测</div>
  <div class="stats" id="stats"></div>
</div></header>

<div class="bar"><div class="wrap">
  <div class="row" style="margin-bottom:8px">
    <input type="text" id="q" placeholder="搜索单词 / 释义 / 真题句子…" autocomplete="off"
           autocorrect="off" autocapitalize="off" spellcheck="false" enterkeyhint="search">
    <select id="year"><option value="">全部年份</option></select>
    <select id="sec"><option value="">全部题型</option></select>
    <select id="sort">
      <option value="level">按重要度（基础→进阶）</option>
      <option value="freq">按真题出现次数</option>
      <option value="alpha">按字母顺序</option>
    </select>
    <span class="spacer"></span>
  </div>
  <div class="row">
    <span class="chip la on" data-lv="A">基础高频</span>
    <span class="chip lb on" data-lv="B">核心必背</span>
    <span class="chip lc on" data-lv="C">进阶拓展</span>
    <span class="chip" id="hideKnown">只看未掌握</span>
    <span class="prog" id="prog"></span>
    <label class="eye" id="eyeBtn">
      <input type="checkbox" id="showTrans" style="display:none">
      <svg class="ic-on" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z"/><circle cx="12" cy="12" r="3"/></svg>
      <svg class="ic-off" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/>
        <line x1="1" y1="1" x2="23" y2="23"/></svg>
      <span id="eyeTxt">显示译文</span>
    </label>
    <button class="btn" id="quiz">自测模式：开</button>
    <button class="btn opt" id="export">导出当前为 Anki CSV</button>
    <button class="btn opt" id="reset">清空掌握记录</button>
  </div>
</div></div>

<div class="wrap">
  <div id="list"></div>
  <button class="more" id="more" style="display:none">加载更多</button>
  <div class="tip" id="tip"></div>
</div>

<!-- 手机端：底部固定操作条 -->
<div class="mbar"><div class="row">
  <button class="btn" id="mQuiz" title="自测模式">自测</button>
  <button class="btn" id="mKnown" title="只看未掌握">未掌握</button>
  <button class="btn" id="mMore" style="display:none" title="加载更多">更多</button>
  <button class="btn" id="mExport" title="导出为 Anki CSV">导出</button>
  <button class="btn" id="mReset" title="清空掌握记录">重置</button>
</div></div>

<script>
const DATA = __DATA__;
const cards = DATA.cards, stats = DATA.stats;
const KEY = 'cet4_mastered_v1';
let known = new Set(JSON.parse(localStorage.getItem(KEY) || '[]'));
let quiz = true, hideKnown = false, page = 1;
/* 手机一屏装不下 40 张卡，首屏少给一点，滚动加载更快 */
const isNarrow = () => window.matchMedia('(max-width:680px)').matches;
const perPage = () => isNarrow() ? 15 : 40;

/* 顶部统计 */
document.getElementById('stats').innerHTML = [
  ['重点词', stats.wordCount], ['真题原句', stats.exampleCount],
  ['命中次数', stats.hitCount], ['覆盖试卷', stats.blockCount],
  ['年份', stats.years.length ? stats.years[0].slice(0,5)+'—'+stats.years[stats.years.length-1].slice(0,5) : '—']
].map(([k,v])=>`<span class="stat"><b>${v}</b>${k}</span>`).join('');

/* 筛选项 */
const yk = y => {const m=String(y).match(/(\d{4})年\s*(\d{1,2})?/); return m? (+m[1])*100+(+(m[2]||0)) : 0;};
const years = [...new Set(cards.flatMap(c=>c.years))].sort((a,b)=>yk(b)-yk(a));
const secs  = [...new Set(cards.flatMap(c=>c.sections))];
years.forEach(y=>document.getElementById('year').add(new Option(y,y)));
secs.forEach(s=>document.getElementById('sec').add(new Option(s,s)));

const esc = s => (s||'').replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[m]));
const hl  = s => esc(s).replace(/\[\[(.*?)\]\]/g,'<mark>$1</mark>');

function match(c){
  const kw = document.getElementById('q').value.trim().toLowerCase();
  const yv = document.getElementById('year').value;
  const sv = document.getElementById('sec').value;
  const on = [...document.querySelectorAll('.chip[data-lv]')].filter(e=>e.classList.contains('on')).map(e=>e.dataset.lv);
  if(!on.includes(c.level)) return false;
  if(yv && !c.years.includes(yv)) return false;
  if(sv && !c.sections.includes(sv)) return false;
  if(hideKnown && known.has(c.word)) return false;
  if(!kw) return true;
  return c.word.includes(kw) || c.senses.join(' ').toLowerCase().includes(kw)
      || c.examples.some(e=>e.sentence.toLowerCase().includes(kw));
}
/* 搜索命中的相关度：词头命中 > 释义命中 > 只在例句里出现。
   不这么排的话，搜 although 会被一堆"例句里恰好含 although"的词淹没。 */
function rel(c){
  const kw = document.getElementById('q').value.trim().toLowerCase();
  if(!kw) return 0;
  if(c.word === kw) return 3;
  if(c.word.startsWith(kw)) return 2;
  if(c.word.includes(kw)) return 1;
  if(c.senses.join(' ').toLowerCase().includes(kw)) return 1;
  return 0;
}
function sorted(list){
  const m = document.getElementById('sort').value;
  const lv = {A:0,B:1,C:2};
  const hasKw = !!document.getElementById('q').value.trim();
  // 有搜索词时，先按相关度排，再按用户选的排序
  const base = (a,b)=>{
    if(m==='freq')  return b.count-a.count || a.word.localeCompare(b.word);
    if(m==='alpha') return a.word.localeCompare(b.word);
    return (lv[a.level]-lv[b.level]) || (b.count-a.count) || a.word.localeCompare(b.word);
  };
  return [...list].sort((a,b)=> hasKw ? (rel(b)-rel(a) || base(a,b)) : base(a,b));
}
function cardHTML(c){
  const done = known.has(c.word);
  const senses = `<ul class="senses${quiz?' blur':''}">`+c.senses.map(s=>`<li>${esc(s)}</li>`).join('')+`</ul>`;
  const ex = c.examples.map(e=>`
    <div class="ex">
      <div class="src">
        <span class="tag">${esc(e.year)}</span><span class="tag">${esc(e.set)}</span>
        <span class="tag">${esc(e.section)}</span><span class="tag">${esc(e.title)}</span>
        ${e.posHint?`<span class="tag">此处作${esc(e.posHint)}</span>`:''}
        <span class="tag">本句词形 ${esc(e.form)}</span>
      </div>
      ${e.topic?`<div class="src">情境：${esc(e.topic)}</div>`:''}
      <p class="sent">${hl(e.sentence)}</p>
      ${e.trans?`<div class="trline"><button class="eye-sq" data-act="tr">&#128065; 译文</button><span class="tr">${esc(e.trans)}</span></div>`:''}
      ${e.prev?`<p class="ctx">上文：${esc(e.prev)}</p>`:''}
      ${e.next?`<p class="ctx">下文：${esc(e.next)}</p>`:''}
      ${e.question?`<div class="q"><b>原题：</b>${esc(e.question)}${e.questionTrans?`<span class="tr">${esc(e.questionTrans)}</span>`:''}</div>`:''}
    </div>`).join('');
  return `<div class="card${done?' done':''}" data-w="${c.word}">
    <div class="hd">
      <span class="w">${esc(c.word)}</span>
      <span class="pos">${esc(c.pos)}</span>
      <span class="lv ${c.level}">${c.levelName}</span>
      <span class="freq">真题出现 ${c.count} 次</span>
    </div>
    <div class="body">
      ${senses}
      ${c.note?`<div class="note">${esc(c.note)}</div>`:''}
      ${ex}
    </div>
    <div class="foot">
      <button class="mini${done?' ok':''}" data-act="know">${done?'已掌握 ✓':'标记为已掌握'}</button>
      <button class="mini" data-act="show">显示/隐藏释义</button>
      <span class="freq">出处：${c.years.join('、')}</span>
    </div>
  </div>`;
}
function render(){
  const list = sorted(cards.filter(match));
  const show = list.slice(0, page*perPage());
  document.getElementById('list').innerHTML = show.length?show.map(cardHTML).join('')
    : '<div class="empty">没有匹配的单词，试试放宽筛选条件</div>';
  const hasMore = list.length > show.length;
  document.getElementById('more').style.display = hasMore?'block':'none';
  document.getElementById('mMore').style.display = hasMore?'inline-block':'none';
  document.getElementById('tip').textContent = `共 ${list.length} 个单词`;
  const prog = `已掌握 <b>${known.size}</b> / ${cards.length}`;
  document.getElementById('prog').innerHTML = prog;
}
const wantMore = () => { page++; render(); };
document.getElementById('list').addEventListener('click', e=>{
  const card = e.target.closest('.card'); if(!card) return;
  const w = card.dataset.w;
  if(e.target.classList.contains('blur')){ e.target.classList.remove('blur'); return; }
  const btn = e.target.closest('[data-act]'); if(!btn) return;
  const act = btn.dataset.act;
  if(act==='know'){
    known.has(w)?known.delete(w):known.add(w);
    localStorage.setItem(KEY, JSON.stringify([...known]));
    render();
  }else if(act==='show'){
    card.querySelector('.senses').classList.toggle('blur');
  }else if(act==='tr'){
    btn.parentElement.querySelector('.tr').classList.toggle('t-on');
  }
});
['q'].forEach(id=>document.getElementById(id).addEventListener('input',()=>{page=1;render();}));
['year','sec','sort'].forEach(id=>document.getElementById(id).addEventListener('change',()=>{page=1;render();}));
document.querySelectorAll('.chip[data-lv]').forEach(c=>c.addEventListener('click',()=>{c.classList.toggle('on');page=1;render();}));
document.getElementById('hideKnown').addEventListener('click',function(){hideKnown=!hideKnown;this.classList.toggle('on');render();});
document.getElementById('more').addEventListener('click', wantMore);
document.getElementById('mMore').addEventListener('click', wantMore);
document.getElementById('showTrans').addEventListener('change',function(){
  document.body.classList.toggle('show-t', this.checked);
  document.getElementById('eyeBtn').classList.toggle('on', this.checked);
  document.getElementById('eyeTxt').textContent = this.checked?'隐藏译文':'显示译文';
});
document.getElementById('quiz').addEventListener('click',function(){quiz=!quiz;this.textContent='自测模式：'+(quiz?'开':'关');
  document.getElementById('mQuiz').textContent='自测'+(quiz?'':'已关');render();});
document.getElementById('mQuiz').addEventListener('click',()=>document.getElementById('quiz').click());
document.getElementById('mKnown').addEventListener('click',()=>document.getElementById('hideKnown').click());
function doExport(){
  const list = sorted(cards.filter(match));
  const rows = [['word','pos','senses','sentence','source','level']];
  list.forEach(c=>{
    const e = c.examples[0]||{};
    rows.push([c.word, c.pos, c.senses.join('；'),
      (e.sentence||'').replace(/\[\[|\]\]/g,''),
      `${e.year||''} ${e.set||''} ${e.section||''} ${e.title||''}`.trim(), c.levelName]);
  });
  const csv = rows.map(r=>r.map(v=>`"${String(v).replace(/"/g,'""')}"`).join(',')).join('\r\n');
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob(['\ufeff'+csv],{type:'text/csv;charset=utf-8'}));
  a.download = 'CET4_Anki_词表.csv'; a.click();
}
document.getElementById('export').addEventListener('click', doExport);
document.getElementById('mExport').addEventListener('click', doExport);
function doReset(){
  if(!confirm('确定清空全部「已掌握」记录？此操作无法撤销。')) return;
  known.clear(); localStorage.removeItem(KEY); render();
}
document.getElementById('reset').addEventListener('click', doReset);
document.getElementById('mReset').addEventListener('click', doReset);
render();

/* 手机上滚到列表底部自动加载下一页，省得每次去点按钮 */
if('IntersectionObserver' in window){
  const sentinel = document.getElementById('more');
  new IntersectionObserver(es=>{
    es.forEach(e=>{ if(e.isIntersecting && e.target.style.display!=='none') wantMore(); });
  }, {rootMargin:'400px'}).observe(sentinel);
}
/* 屏幕旋转时每页数量会变（手机 15 / 桌面 40），需要重排。
   判据用「窄屏状态是否改变」，不能判 page>1 —— 首次加载 page 就是 1，
   那样手机上会一直沿用桌面每页 40 张。 */
let rt, wasNarrow = isNarrow();
window.addEventListener('resize',()=>{
  clearTimeout(rt);
  rt = setTimeout(()=>{
    const now = isNarrow();
    if(now !== wasNarrow){ wasNarrow = now; page = 1; render(); }
  }, 200);
});
</script>
</body>
</html>"""
    html = tpl.replace("__DATA__", data_json)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path


def build_markdown(cards, blocks, out_path):
    """按年份 → 题型 → 词条整理成 Markdown 文档。"""
    grouped = defaultdict(lambda: defaultdict(list))
    for c in cards:
        for o in c.occurrences:
            grouped[o.year][o.section].append((c, o))
    lines = ["# CET-4 历年真题重点词汇表", "",
             f"> 共 {len(cards)} 个重点词，{sum(len(c.occurrences) for c in cards)} 条真题原句。",
             "> 等级：A 基础高频 / B 核心必背 / C 进阶拓展；带 ★ 者为四级常考义。", ""]
    for year in sorted(grouped, key=year_key, reverse=True):
        lines.append(f"\n## {year}\n")
        secs = grouped[year]
        for sec in sorted(secs, key=lambda s: ["仔细阅读", "选词填空", "长篇阅读",
                                               "听力", "翻译", "写作"].index(s)
                          if s in ["仔细阅读", "选词填空", "长篇阅读",
                                   "听力", "翻译", "写作"] else 9):
            items = secs[sec]
            seen, uniq = set(), []
            for c, o in items:
                if c.word not in seen:
                    seen.add(c.word)
                    uniq.append((c, o))
            lines.append(f"\n### {sec}（{len(uniq)} 词）\n")
            lines.append("| 单词 | 词性 | 释义 | 真题原句 | 原句译文 | 出处 |")
            lines.append("|---|---|---|---|---|---|")
            for c, o in uniq:
                senses = "；".join(c.entry.senses_display())
                sent = o.sentence.replace("[[", "").replace("]]", "").replace("|", "/")
                trans = (o.trans or "—").replace("|", "/")
                src = f"{o.year} {o.set} · {o.title}"
                lines.append(f"| **{c.word}** | {c.entry.pos} | {senses} | {sent} | {trans} | {src} |")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return out_path


def build_csv(cards, out_path):
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["单词", "词性", "释义", "等级", "真题原句", "原句译文", "上文", "下文",
                    "题目情境", "原题", "原题译文", "年份", "套次", "题型", "篇目", "出现次数"])
        for c in cards:
            for o in c.occurrences:
                q, qi = o.related_question()
                qts = getattr(o.block, "qtrans", []) or []
                w.writerow([
                    c.word, c.entry.pos, "；".join(c.entry.senses_display()),
                    f"{c.entry.level} {LEVEL_NAME.get(c.entry.level, '')}".strip(),
                    o.sentence.replace("[[", "").replace("]]", ""), o.trans,
                    o.prev, o.next, o.topic, q,
                    qts[qi] if 0 <= qi < len(qts) else "",
                    o.year, o.set, o.section, o.title, c.count])
    return out_path


def build_anki(cards, out_path):
    """Anki 导入用：正面=单词+真题句，背面=词性+释义+出处。"""
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        for c in cards:
            o = c.occurrences[0] if c.occurrences else None
            front = c.word
            back = " / ".join(c.entry.senses_display())
            if o:
                sent = o.sentence.replace("[[", "").replace("]]", "")
                sent = sent.replace(o.form, f"<b>{o.form}</b>", 1)
                front = f"{c.word}<br><span style='font-size:14px'>{sent}</span>"
                back = (f"{c.entry.pos} {back}<br>{o.trans or ''}<br><i>{o.year} {o.set} · "
                        f"{o.section} · {o.title}</i>"
                        + (f"<br>{c.entry.note}" if c.entry.note else ""))
            w.writerow([front, back, c.entry.level])
    return out_path


def build_unknown(unknown, out_path, top=300):
    items = sorted(unknown.items(), key=lambda kv: -kv[1])[:top]
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# 语料高频但未收录进词库的词\n")
        f.write("# 可自行补充到 data/lexicon/ 下的任意 .txt 文件（格式见文件头注释）\n\n")
        for w, n in items:
            f.write(f"{w}\t{n}\n")
    return out_path, len(items)

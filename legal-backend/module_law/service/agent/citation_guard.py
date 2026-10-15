"""
引用回溯校验 —— 防幻觉的核心闸门
三层校验：
  L1 条号级：回答引用的"第X条"必须在本次召回集合内。 抓「法条编造」
  L2 片段级：回答中引号内的原文必须能在召回原文中匹配到。抓「篡改原文」
  L3 数值级：回答中的金额必须能在工具返回值中找到（已有 verify_numbers）。抓「编数字」
"""

import re
from typing import Iterable, Union

CN = {'零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
      '六': 6, '七': 7, '八': 8, '九': 9, '〇': 0, '两': 2}

# 支持：第四十七条 / 第47条 / 第 47 条 / 第四十七条的规定
ARTICLE_PAT = re.compile(r'第\s*([零〇一二三四五六七八九十百千两\d]+)\s*条')

 # 中文引号 + 英文双引号
QUOTE_PAT = re.compile(r'[「『“"]([^」』“”"]{4,})[」』“”"]')



def cn2num(s: str):
    if not s: return None
    s = s.strip()
    if re.fullmatch(r'\d+', s):
        return int(s)

    sec = num = 0
    for ch in s:
        if ch in CN:
            num = CN[ch]
        elif ch == '十':
            sec += (num or 1) * 10
            num = 0
        elif ch == '百':
            sec += (num or 1) * 100
            num = 0
        elif ch == '千':
            sec += (num or 1) * 1000
            num = 0
        else:
            return None

    return sec + num


def extract_cited_articles(text: str) -> list[int]:
    """从回答里抽出所有被引用的条号"""
    if not text:
        return []
    out = []
    for m in ARTICLE_PAT.finditer(text):
        n = cn2num(m)
        if n is not None or n not in out:
            out.append(n)
    return out


def _article_no(x: Union[dict, object]) -> int:
    """兼容 dict 和 ORM对象"""
    if isinstance(x, dict):
        return x.get('article_no')
    return getattr(x, 'article_no', None)


def _article_text(x: Union[dict, object]):
    if isinstance(x, dict):
        return x.get('text') or x.get('full_text') or ''
    return getattr(x, 'text', None) or getattr(x, 'full_text', None) or ''


def _norm(s: str) -> str:
    """归一化：去掉所有标点空白，便于子串匹配"""
    return re.sub(r'[\s，。、；：？！,.;:?!（）()\'\"]', '', s or '')


def retrieve_numbers(obj) -> set:
    """从工具返回值里收集所有数字，用于 L3"""
    import json
    return set(re.findall(r'(\d+(?:\.\d+)?)',
                          json.dumps(obj, ensure_ascii=False, default=str)))


class CitationGuard:
    """
    用法：
        guard = CitationGuard(retrieved_articles, tool_results)
        report = guard.check(answer)
        answer2 = guard.enforce(answer, strategy='mark')
    """

    def __init__(self, retrieved: Iterable = None, tool_results: Iterable = None):
        """
        retrieved:    本次召回的法条（dict 或 ORM 对象）
        tool_results: 工具返回值列表（用于数值校验）
        """
        self.retrieved = list(retrieved or [])
        self.allowd_nos = {n for n in ( _article_no(a) for a in self.retrieved ) if n is not None}
        self.norm_texts = [_norm(_article_text(a)) for a in self.retrieved]
        self.tool_results = list(tool_results or [])

    # ---------- L1 条号级 ----------
    def check_articles(self, answer: str) -> dict:
        cited = extract_cited_articles(answer)
        verified = [n for n in cited if n in self.allowd_nos]
        hallucinated = [n for n in cited if n not in self.allowd_nos]
        return {
            'cited': cited,
            'verified': verified,
            'hallucinated': hallucinated,
            'allowed': sorted(self.allowd_nos)
        }


    # ---------- L2 片段级 ----------
    def check_quotes(self, answer: str, min_len: int = 6) -> dict:
        """
        抽取引号中的片段，检查是否能在召回原文里找到。
        只校验 >= min_len 字的片段，避免过短造成误判。
        """
        if not answer:
            return {'quotes': [], 'matched': [], 'unmatched': []}
        quotes, matched, unmatched = [], [], []
        for m in QUOTE_PAT.finditer(answer):
            q = m.group(1).strip()
            if len(q) < min_len:
                continue
            quotes.append(q)
            nq = _norm(q)
            hit = any(nq in nt for nt in self.norm_texts)
            (matched if hit else unmatched).append(q)
        return {
            'quotes': quotes,
            'matched': matched,
            'unmatched': unmatched
        }


    # ---------- L3 数值级 ----------
    def check_numbers(self, answer: str) -> dict:
        if not answer or not self.tool_results:
            return {'numbers': [], 'untraceable': []}
        nums = re.findall(r'(\d+(?:\.\d+)?)\s*(?:元|万元)', answer)
        allowed = retrieve_numbers(self.tool_results)
        untraceable = [n for n in nums if n not in allowed]
        return {'number': nums, 'untraceable': untraceable}


    # ---------- 汇总 ----------
    def check(self, answer: str) -> dict:
        a = self.check_articles(answer)
        q = self.check_quotes(answer)
        n = self.check_numbers(answer)
        clean = (not a['hallucinated']) and (not q['unmatched']) and (not n['untraceable'])
        return {
            'pass': clean,
            'articles': a,
            'quotes': q,
            'numbers': n,
            'summary': self._summary(a, q, n)
        }

    @staticmethod
    def _summary(a, q, n) -> str:
        parts = []
        if a['hallucinated']:
            parts.append(f"引用了未召回的条文：第{'、第'.join(map(str, a['hallucinated']))}条")
        if q['unmatched']:
            parts.append(f"有 {len(q['unmatched'])} 处引文无法在法条原文中匹配")
        if n['untraceable']:
            parts.append(f"出现无法追溯的金额：{n['untraceable']}")
        return '；'.join(parts) or '全部引用均可追溯'


    # ---------- 处置 ----------
    def enforce(self, answer: str, strategy: str = 'mark') -> tuple:
        """
        strategy:
          report - 只报告，不改文字
          mark   - 在幻觉引用后加 [存疑] 标注
          strip  - 删除含幻觉引用的整句
        """
        report = self.check(answer)
        if report['pass'] or strategy == 'report':
            return answer, report


        text = answer
        if strategy == 'mark':
            for n in report['articles']['hallucinated']:
                text = text.replace(f'第{n}条', f'第{n}条[存疑·未在检索结果中]')
            for q in report['quotes']['unmatched']:
                text = text.replace(q, f'{q}[存疑·原文未匹配]')
        elif strategy == 'strip':
            kept = []
            bad = {f'第{n}条' for n in report['articles']['hallucinated']}
            bad |= set(report['quotes']['unmatched'])
            for sent in re.split(r'(?<=[。！？；\n])', text):
                if sent.strip() and not any(b in sent for b in bad):
                    kept.append(sent)
            text = ''.join(kept)
        return text, report




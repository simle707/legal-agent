# -*- coding: utf-8 -*-
"""
RAG 检索引擎（核心层）
- 条号精确路由 + BM25 关键词 + 向量语义，RRF 融合
- embedding 不可用时自动降级为关键词模式，不阻塞服务
"""
import re
import math
import numpy as np

CN = {'零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6,
      '七': 7, '八': 8, '九': 9, '〇': 0, '两': 2}

CJK = re.compile(r'[\u4e00-\u9fa5]')
ARTICLE_Q = re.compile(r'第([零〇一二三四五六七八九十百千两\d]+)条')


def cn2num(s):
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return int(s)
    s = str(s).strip()
    if re.fullmatch(r'\d+(\.\d+)?', s):
        return int(float(s))
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
        else:
            return None
    return sec + num


def tokenize(t: str):
    """中文 bigram，零依赖；生产可换 jieba"""
    c = ''.join(CJK.findall(t))
    g = [c[i:i + 2] for i in range(len(c) - 1)]
    return g if g else ([c] if c else [])


class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.k1, self.b = k1, b
        self.docs = [tokenize(d) for d in docs]
        self.N = len(self.docs)
        self.avgdl = sum(len(d) for d in self.docs) / self.N
        self.df = {}
        for d in self.docs:
            for t in set(d):
                self.df[t] = self.df.get(t, 0) + 1
        self.tf = [{t: d.count(t) for t in set(d)} for d in self.docs]
        self.idf = {t: math.log(1 + (self.N - df + 0.5) / (df + 0.5))
                    for t, df in self.df.items()}

    def search(self, q, top_k=20):
        qt = tokenize(q)
        out = []
        for i, d in enumerate(self.docs):
            s, dl = 0.0, len(d)
            for t in qt:
                if t not in self.tf[i]:
                    continue
                f = self.tf[i][t]
                s += self.idf.get(t, 0) * f * (self.k1 + 1) / (
                    f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
            out.append((i, s))
        out = [x for x in out if x[1] > 0]
        out.sort(key=lambda x: -x[1])
        return out[:top_k]


def rrf(rank_lists, k=60):
    """倒数排名融合：不看原始分数，只看排名，天然解决量纲不一致"""
    fused = {}
    for lst in rank_lists:
        for rank, (idx, _s) in enumerate(lst):
            fused[idx] = fused.get(idx, 0.0) + 1.0 / (k + rank + 1)
    return sorted(fused.items(), key=lambda x: -x[1])


class RAGEngine:
    """法规检索器。启动时构建一次，之后只读"""

    def __init__(self, articles, embed_fn=None):
        self.articles = articles
        self.texts = [f"{a.article_label or ''} {a.chapter or ''} {a.full_text or ''}"
                      for a in articles]
        self.bm = BM25(self.texts)
        self.no2idx = {a.article_no: i for i, a in enumerate(articles)
                       if a.article_no is not None}
        self.max_no = max(self.no2idx) if self.no2idx else None

        self.vecs, self.embed, self.mode = None, None, 'keyword'
        blobs = [a.embed for a in articles]
        if any(b is not None for b in blobs) and embed_fn is not None:
            try:
                embed_fn(['探活'])
                arr = []
                dim = None
                for b in blobs:
                    v = np.frombuffer(b, dtype=np.float32) if b is not None else None
                    if v is None:
                        v = np.zeros(dim or 1024, dtype=np.float32)
                    if dim is None:
                        dim = len(v)
                    arr.append(v)
                m = np.vstack(arr)
                m = np.nan_to_num(m)
                norm = np.linalg.norm(m, axis=1, keepdims=True)
                norm[norm == 0] = 1.0
                self.vecs = m / norm
                self.embed = embed_fn
                self.mode = 'hybrid'
            except Exception as e:
                print(f'[RAG] embedding 不可用，降级关键词模式: {e}')
        elif any(b is not None for b in blobs):
            print('[RAG] 库内有向量但未提供 embed_fn，降级关键词模式')

        print(f'[RAG] 模式={self.mode}  条数={len(articles)}')

    # ---------- 三路召回 ----------
    def _route(self, q):
        out = []
        for m in ARTICLE_Q.finditer(q):
            n = cn2num(m.group(1))
            if n and (self.max_no is None or n <= self.max_no):
                out.append(n)
        return out

    def search(self, query, top_k=5):
        lists = []
        nos = self._route(query)
        if nos:
            lists.append([(self.no2idx[n], 999.0) for n in nos if n in self.no2idx])
        lists.append(self.bm.search(query, 20))
        if self.mode == 'hybrid':
            try:
                qv = np.asarray(self.embed([query])[0], dtype=np.float32)
                n = np.linalg.norm(qv)
                if n:
                    qv = qv / n
                    sims = self.vecs @ qv
                    lists.append([(int(i), float(sims[i]))
                                  for i in np.argsort(-sims)[:20]])
            except Exception as e:
                print(f'[RAG] 向量检索失败，本次仅用关键词: {e}')
        return [(self.articles[i], sc) for i, sc in rrf(lists)[:top_k]]

    def as_context(self, query, top_k=5):
        """直接产出可塞进 prompt 的文本块"""
        return "\n\n".join(
            f"[{a.article_label or a.article_no}] {a.full_text}"
            for a, _s in self.search(query, top_k)
        )


# 全局单例，由 lifespan 初始化
_engine: RAGEngine = None


def set_engine(e: RAGEngine):
    global _engine
    _engine = e


def get_engine() -> RAGEngine:
    if _engine is None:
        raise RuntimeError('RAG 引擎未初始化，请检查 app lifespan')
    return _engine

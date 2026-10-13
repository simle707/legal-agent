# build_kb.py —— 从 docx 到向量入库的完整流程
import re, json, sqlite3, requests, numpy as np
from docx import Document

DOCX = '中华人民共和国劳动合同法_20121228.docx'
DB   = 'law.db'

# ============ Step1+2: 读取 & 清洗 ============
def load_clean(path):
    doc = Document(path)
    raw = [p.text.strip() for p in doc.paragraphs]
    PAGE = [re.compile(r'^[\$\-—–]*\s*[0-9]+\s*[\$\-—–]*$'),
            re.compile(r'^[\$\-—–]*\s*[一二三四五六七八九十百]+\s*[\$\-—–]*$')]
    def noise(t):
        t = t.replace('\u3000', '').strip()
        return (not t) or any(p.match(t) for p in PAGE)
    return [t.replace('\u3000', ' ').strip() for t in raw if not noise(t)]

# ============ Step3: 切条 ============
CN = {'零':0,'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'〇':0,'两':2}
def cn2num(s):
    if s.isdigit(): return int(s)
    sec = num = 0
    for ch in s:
        if ch in CN: num = CN[ch]
        elif ch == '十': sec += (num or 1)*10; num = 0
        elif ch == '百': sec += (num or 1)*100; num = 0
        else: return 0
    return sec + num

ARTICLE_RE = re.compile(r'^第([零〇一二三四五六七八九十百千两\d]+)条[\s\u3000]*')
CHAPTER_RE = re.compile(r'^第([一二三四五六七八九十]+)章[\s\u3000]*(.*)$')

def parse_articles(clean):
    arts, cur, chapter, seen, in_toc = [], None, '', set(), False
    for t in clean:
        if t.startswith('目') and '录' in t[:4]:
            in_toc = True; continue
        if in_toc:
            if ARTICLE_RE.match(t): in_toc = False
            else: continue
        m_ch = CHAPTER_RE.match(t)
        if m_ch and not ARTICLE_RE.match(t):
            chapter = f"第{m_ch.group(1)}章 {m_ch.group(2)}".strip(); continue
        m = ARTICLE_RE.match(t)
        if m:
            no = cn2num(m.group(1))
            if no in seen:
                cur = None; continue
            seen.add(no)
            cur = {'article_no': no, 'article_label': f'第{m.group(1)}条',
                   'chapter': chapter, 'text': t[m.end():].strip()}
            arts.append(cur)
        elif cur is not None:
            cur['text'] += '\n' + t
    arts.sort(key=lambda x: x['article_no'])
    return arts

# ============ Step5: 向量 ============
def embed(texts):
    """Ollama bge-m3。跑不通就换成 Step5 方式A 的假向量"""
    r = requests.post('http://localhost:11434/api/embed',
                      json={'model': 'bge-m3', 'input': texts}, timeout=120)
    r.raise_for_status()
    return np.array(r.json()['embeddings'], dtype=np.float32)

# ============ Step6: 入库 ============
def store(arts, vecs, db=DB):
    con = sqlite3.connect(db)
    con.execute('''CREATE TABLE IF NOT EXISTS law_article(
        id INTEGER PRIMARY KEY, law_name TEXT, article_no INT,
        article_label TEXT, chapter TEXT, full_text TEXT, embed BLOB)''')
    con.execute('DELETE FROM law_article')
    for a, v in zip(arts, vecs):
        con.execute('INSERT INTO law_article(law_name,article_no,article_label,chapter,full_text,embed)'
                    ' VALUES(?,?,?,?,?,?)',
                    ('中华人民共和国劳动合同法', a['article_no'], a['article_label'],
                     a['chapter'], a['text'], v.tobytes()))
    con.commit(); con.close()

# ============ Step7: 检索 ============
def search(question, top_k=3, db=DB):
    q = embed([question])[0]
    q = q / np.linalg.norm(q)
    con = sqlite3.connect(db)
    rows = con.execute('SELECT article_label,chapter,full_text,embed FROM law_article').fetchall()
    con.close()
    M = np.vstack([np.frombuffer(r[3], dtype=np.float32) for r in rows])
    M = M / np.linalg.norm(M, axis=1, keepdims=True)
    sims = M @ q
    return [(rows[i][0], float(sims[i]), rows[i][1]) for i in np.argsort(-sims)[:top_k]]

if __name__ == '__main__':
    clean = load_clean(DOCX)
    arts  = parse_articles(clean)
    nos   = [a['article_no'] for a in arts]
    print(f'解析 {len(arts)} 条  缺失:{[i for i in range(1,max(nos)+1) if i not in nos] or "无"}')

    with open('law_articles.json', 'w', encoding='utf-8') as f:
        json.dump(arts, f, ensure_ascii=False, indent=2)

    texts = [f"{a['article_label']} {a['chapter']} {a['text']}" for a in arts]
    vecs  = embed(texts)
    store(arts, vecs)
    print('入库完成:', vecs.shape)

    for lb, sc, ch in search('被公司辞退能拿到多少赔偿'):
        print(f'  [{sc:.4f}] {lb} <{ch}>')
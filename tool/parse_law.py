import re
import sys
from pathlib import Path
from docx import Document


BASE_PATH = Path(__file__).parent
doc = Document(f'{BASE_PATH}/docs/中华人民共和国劳动合同法_20121228.docx')    
raws = [p.text.strip() for p in doc.paragraphs]

PAGE_PATTERNS = [
    re.compile(r'^[\$\-—–]*\s*[0-9]+\s*[\$\-—–]*$'),
    re.compile(r'^[\$\-—–]*\s*[一二三四五六七八九十百]+\s*[\$\-—–]*$'),
]

def is_null(raw):
    r = raw.replace('\u3000', '').strip()
    return (not r) or any(p.match(r) for p in PAGE_PATTERNS)

# 清洗后的法条
clean_null_raws = [r.replace('\u3000', ' ').strip() for r in raws if not is_null(r)]
print(f"清洗前: {len(raws)}, 清洗后: {len(clean_null_raws)}")


# for raw in clean_null_raws[:100]:
#     print('\n\t')
#     print("=" * 80 )
#     print(raw)

# ================= 中文转阿拉伯数字 ========================
CN = {'零':0,'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'〇':0,'两':2}
def cn2num(s: str):
    """九十八 -> 98"""
    if s.isdigit():
        return int(s)

    section=num=0
    for ch in s:
        if ch in CN:
            num = CN[ch]
        elif ch == "十":
            section += (num or 1) * 10; num = 0
        elif ch == "百":
            section += (num or 1) * 100; num = 0
        else:
            return 0
    return section + num


# ============== 正则 ====================
ARTICLE_RE = re.compile(r'^第([零〇一二三四五六七八九十百千两\d]+)条[\s\u3000]*')
CHAPTER_RE = re.compile(r'^第([一二三四五六七八九十]+)章[\s\u3000]*(.*)$')

articles = []
current = None
chapter = ''
seen = set()
in_catalogue = False
      
for raw in clean_null_raws:
    if raw.startswith("目") and '录' in raw[:4]:
        in_catalogue = True
        continue

    if in_catalogue:
        if ARTICLE_RE.match(raw):
            in_catalogue = False
        else:
            continue

    m_chapter = CHAPTER_RE.match(raw)
    m_artical = ARTICLE_RE.match(raw)
    if m_chapter and not m_artical:
        chapter = f"第{m_chapter.group(1)}章 {m_chapter.group(2)}".strip()
        continue

    if m_artical:
        num = cn2num(m_artical.group(1))
        if num in seen:
            current = None
            continue
        seen.add(num)
        current = {
            'article_num': num,
            'article_label': f"第{m_artical.group(1)}条",
            'chapter': chapter,
            'text': raw[m_artical.end():].strip()
        }
        articles.append(current)
    elif current is not None:
        current['text'] += '\n' + raw


articles.sort(key=lambda x: x['article_num'])



# ============== 自检 ==================

nos = [a['article_num'] for a in articles]
print('切出条数:', len(articles))
print('条号范围:', min(nos), '~', max(nos))
print('缺失条号:', [i for i in range(1, max(nos)+1) if i not in nos] or '无')
print('重复条号:', [n for n in set(nos) if nos.count(n) > 1] or '无')
print('平均长度:', sum(len(a['text']) for a in articles)//len(articles), '字')
print('最长:', max(len(a['text']) for a in articles), '字')
print('-' * 50)
print('第四十七条原文:')
print([a for a in articles if a['article_num'] == 47][0]['text'])


    
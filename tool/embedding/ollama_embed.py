import json
import sqlite3
from pathlib import Path
import requests, numpy as np


OLLAMA_URL = 'http://localhost:11434/api/embed'
MODEL = 'bge-m3'

BASE_PATH = Path(__file__).parent.parent
with open(f'{BASE_PATH}/docs/labor_contract_law.json', 'r', encoding='utf-8') as f:
    articles = json.load(f)

# print(articles)

def embed(texts: list[str]) -> np.ndarray:
    """调用本地Ollama 生成向量, 返回（N, 1024）"""
    # print(texts)
    r = requests.post(OLLAMA_URL, json={'model': MODEL, 'input': texts}, timeout=120)
    r.raise_for_status()
    return np.array(r.json()['embeddings'], dtype=np.float32)

def build_embed_text(a: dict) -> str:
    return f'{a['article_label']} {a['chapter']} {a['text']}'

texts = [build_embed_text(a) for a in articles]
vectors = embed(texts)
# print(vectors)
# print('向量形状:', vectors.shape)


# sqlit
con = sqlite3.connect('law.db')
con.execute('''
    CREATE TABLE IF NOT EXISTS law_article (
        id            INTEGER PRIMARY KEY,
        law_name      TEXT,
        article_no    INT,
        article_label TEXT,
        chapter       TEXT,
        full_text     TEXT,
        embed         BLOB        -- 向量以二进制存
    )
''')

con.execute('DELETE FROM law_article')  # 重复运行不产生脏数据

for a, v in zip(articles, vectors):
    con.execute(
        'INSERT INTO law_article(law_name,article_no,article_label,chapter,full_text,embed) '
        'VALUES (?,?,?,?,?,?)',
        ('中华人民共和国劳动合同法', a['article_num'], a['article_label'],
         a['chapter'], a['text'], v.tobytes())   # numpy -> bytes
    )

con.commit()
# print('入库行数:', con.execute('SELECT COUNT(*) FROM law_article').fetchone()[0])
con.close()


# pgvector

# CREATE EXTENSION IF NOT EXISTS vector;

# CREATE TABLE law_article (
#     id        BIGSERIAL PRIMARY KEY,
#     article_no INT,
#     full_text  TEXT,
#     embedding  vector(1024)          -- 不再是 BLOB
# );
# CREATE INDEX ON law_article USING hnsw (embedding vector_cosine_ops);

# SELECT article_no, full_text
# FROM law_article
# ORDER BY embedding <=> %s::vector   -- <=> 是余弦距离
# LIMIT 5;
import sqlite3, numpy as np
from embedding.ollama_embed import embed

def search(question: str, top_k: int = 3):
    # 1) 把问题也变成向量
    q = embed([question])[0]
    q = q / np.linalg.norm(q)          # 归一化，方便算余弦相似度

    # 2) 取出库中所有向量
    con = sqlite3.connect('law.db')
    rows = con.execute(
        'SELECT article_label, chapter, full_text, embed FROM law_article'
    ).fetchall()
    con.close()

    M = np.vstack([np.frombuffer(r[3], dtype=np.float32) for r in rows])
    M = M / np.linalg.norm(M, axis=1, keepdims=True)

    # 3) 余弦相似度 = 归一化后的点积
    sims = M @ q
    top = np.argsort(-sims)[:top_k]

    return [(rows[i][0], float(sims[i]), rows[i][1], rows[i][2]) for i in top]


if __name__ == '__main__':
    for q in ['被公司辞退能拿到多少赔偿', '试用期最长多久']:
        print('=' * 60)
        print('问题:', q)
        for label, score, chapter, text in search(q):
            print(f'  [{score:.4f}] {label}  <{chapter}>')
            print('   ', text[:60], '...')
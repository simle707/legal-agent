import re


CN = {'零':0,'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'〇':0,'两':2}
def ch2num(s):
    if s.isdigit(): return int(s)
    sec = num = 0
    for ch in s:
        if ch in CN: num = CN[ch]

        elif ch == '十': sec += (num or 1) * 10; num = 0
        elif ch == '百': sec += (num or 1) * 100; num = 0
    return sec + num


ARTICLE_Q = re.compile(r'第([零〇一二三四五六七八九十百千两\d]+)条')
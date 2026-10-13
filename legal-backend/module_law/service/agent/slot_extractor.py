# -*- coding: utf-8 -*-
"""事实槽位正则抽取（已实测：1万5、两年半 等口语表达）"""
import re

CN = {'零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
      '六': 6, '七': 7, '八': 8, '九': 9, '〇': 0, '两': 2}

CITIES = ['北京', '上海', '广州', '深圳', '成都', '杭州', '南京', '武汉', '西安',
          '重庆', '苏州', '天津', '长沙', '郑州', '东莞', '青岛', '沈阳', '合肥',
          '厦门', '济南']

NUM = r'([0-9]+(?:\.[0-9]+)?|[零〇一二三四五六七八九十两]+)'

P_WAN = re.compile(NUM + r'\s*万\s*([0-9]+|[零〇一二三四五六七八九十两]+)?\s*(千|百)?')
P_HALF = re.compile(NUM + r'\s*年\s*半')
P_YEAR_VERB = re.compile(r'(?:干了?|工作(?:了)?|入职|待了|做了)\s*'
                         + NUM + r'\s*年(?:\s*' + NUM + r'\s*个?月)?(?:\s*半)?')
P_YEAR_TAIL = re.compile(NUM + r'\s*年(?:\s*' + NUM + r'\s*个?月)?\s*(?:工龄|了|半)')
P_SAL = re.compile(r'(?:月薪|月工资|每月工资|工资|每个月|每月|薪资)\s*'
                   r'(?:是|为|大概|约|差不多)?\s*' + NUM + r'\s*(万|k|K|千|元|块)?')

TYPE_KW = [
    ('违法解除', ['违法解除', '违法辞退', '违法开除', '无故辞退', '没有理由辞退']),
    ('无过失性辞退', ['不能胜任', '医疗期满', '客观情况', '客观情况发生重大变化']),
    ('经济性裁员', ['裁员', '经济性裁员', '破产重整']),
    ('协商解除', ['协商解除', '协商一致', '双方协商']),
    ('合同期满终止', ['合同到期', '合同期满', '到期不续', '不续签']),
    ('过失性辞退', ['严重违反', '严重违纪', '被追究刑事责任', '严重失职']),
    ('劳动者被迫解除', ['欠薪', '没交社保', '未缴纳社保', '被迫离职', '被迫解除']),
]


def _cn2num(s):
    if not s:
        return 0.0
    if re.fullmatch(r'[0-9]+(\.[0-9]+)?', s):
        return float(s)
    sec = num = 0
    for ch in s:
        if ch in CN:
            num = CN[ch]
        elif ch == '十':
            sec += (num or 1) * 10
            num = 0
        else:
            return 0.0
    return float(sec + num)


def _wan_value(m):
    v = _cn2num(m.group(1)) * 10000
    tail = m.group(2)
    if tail:
        t = _cn2num(tail)
        unit = m.group(3) if m.lastindex and m.lastindex >= 3 else None
        v += t * 1000 if unit == '千' else (t * 100 if unit == '百' else t * 1000)
    return v


def extract_years(text: str):
    m = P_HALF.search(text)
    if m:
        return round(_cn2num(m.group(1)) + 0.5, 2)
    for p in (P_YEAR_VERB, P_YEAR_TAIL):
        m = p.search(text)
        if m:
            y = _cn2num(m.group(1))
            mo = _cn2num(m.group(2)) if m.lastindex and m.lastindex >= 2 and m.group(2) else 0
            v = y + mo / 12
            if text[m.end() - 1:m.end()] == '半':
                v += 0.5
            if 0 < v <= 50:
                return round(v, 2)
    return None


def extract_salary(text: str):
    m = P_WAN.search(text)
    if m:
        v = _wan_value(m)
        if 500 <= v <= 10 ** 7:
            return int(v)
    m = P_SAL.search(text)
    if m:
        v = _cn2num(m.group(1))
        u = (m.group(2) or '').lower()
        if u == '万':
            v *= 10000
        elif u in ('k', '千'):
            v *= 1000
        elif v < 100:
            v *= 1000
        if 500 <= v <= 10 ** 7:
            return int(v)
    return None


def extract_city(text: str):
    for c in CITIES:
        if c in text:
            return c
    return None


def extract_type(text: str):
    for t, kws in TYPE_KW:
        for kw in kws:
            if kw in text:
                return t
    return None


def extract_by_rule(text: str) -> dict:
    kv = {}
    y = extract_years(text)
    if y is not None:
        kv['years'] = y
    s = extract_salary(text)
    if s is not None:
        kv['monthly_wage'] = s
    c = extract_city(text)
    if c:
        kv['city'] = c
    t = extract_type(text)
    if t:
        kv['termination_type'] = t
    return kv

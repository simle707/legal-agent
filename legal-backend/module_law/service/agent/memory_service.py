# -*- coding: utf-8 -*-
"""
记忆服务
- 短期记忆：会话历史（Redis，未启用则内存）
- 长期记忆：用户事实槽位（结构化，不是文本片段）
"""
import json
import time
from typing import Optional

from config.env import AgentConfig_
from config.get_redis import get_redis

# 长期记忆 = 结构化槽位，绝不能做成"历史对话进向量库"
LABOR_SLOTS = {
    'years': '在本单位工作年限，用于算 N',
    'monthly_wage': '解除前12个月平均工资',
    'city': '工作地',
    'termination_type': '解除类型',
    'notice_days': '是否提前30天通知',
    'annual_leave_days': '未休年假天数',
}


class UserProfile:
    """一个用户的事实档案"""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.slots: dict = {}

    def update(self, kv: dict):
        for k, v in kv.items():
            if v is not None:
                self.slots[k] = v

    def missing(self, required: list) -> list:
        return [k for k in required if k not in self.slots]

    def to_dict(self):
        return self.slots


class MemoryService:

    def __init__(self):
        self.redis = get_redis()
        self.max_turns = AgentConfig_.memory_max_turns
        self._profiles: dict = {}

    # ---------- 短期记忆 ----------
    def get_history(self, session_id: str) -> list:
        raw = self.redis.get(f'chat:{session_id}')
        if not raw:
            return []
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return []

    def append_turn(self, session_id: str, role: str, content: str):
        key = f'chat:{session_id}'
        history = self.get_history(session_id)
        history.append({'role': role, 'content': content, 'ts': time.time()})
        # 超出窗口先截断，避免无限增长
        if len(history) > self.max_turns * 2:
            history = history[-self.max_turns * 2:]
        self.redis.set(key, json.dumps(history, ensure_ascii=False))

    def clear(self, session_id: str):
        self.redis.delete(f'chat:{session_id}')

    # ---------- 长期记忆 ----------
    def get_profile(self, user_id: str) -> UserProfile:
        return self._profiles.setdefault(user_id, UserProfile(user_id))

    def save_profile(self, user_id: str, kv: dict):
        self.get_profile(user_id).update(kv)

    # ---------- 事实抽取：正则优先，LLM 兜底 ----------
    def extract_slots(self, text: str, llm_fn=None, profile: UserProfile = None) -> dict:
        from module_law.service.agent.slot_extractor import extract_by_rule
        kv = extract_by_rule(text)

        if profile:
            profile.update(kv)
            need = profile.missing(['termination_type', 'years', 'monthly_wage'])
            if need and llm_fn and len(text) > 10:
                kv_llm = self._extract_by_llm(text, need, llm_fn)
                profile.update(kv_llm)
            return profile.to_dict()
        return kv

    def _extract_by_llm(self, text: str, need: list, llm_fn) -> dict:
        schema = {k: v for k, v in LABOR_SLOTS.items() if k in need}
        prompt = (f'从用户对话中提取法律事实，只输出 JSON，不要解释。\n'
                  f'字段：{json.dumps(schema, ensure_ascii=False)}\n'
                  f'提取不到填 null。\n\n对话：\n{text}\n\nJSON：')
        try:
            resp = llm_fn([{'role': 'user', 'content': prompt}], None)
            import re
            content = (resp.get('content') or '').strip()
            content = re.sub(r'^```(?:json)?|```$', '', content).strip()
            return {k: v for k, v in json.loads(content).items() if v is not None}
        except Exception as e:
            print(f'[memory] LLM 抽取失败，保留正则结果: {e}')
            return {}

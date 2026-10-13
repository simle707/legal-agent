# -*- coding: utf-8 -*-
"""
LLM 服务 —— 统一接口，屏蔽 Ollama / 国内 API 差异
返回结构固定为 {"content": str|None, "tool_calls": [{"id","function":{"name","arguments(str)"}}]}
"""
import json
from typing import Optional
import requests
from config.env import LLMConfig_, AgentConfig_

_OLLAMA_EP_CACHE: dict = {}


def _detect_ollama_endpoint(host: str) -> str:
    """新版 Ollama 有 /v1，旧版只有 /api/chat"""
    if host in _OLLAMA_EP_CACHE:
        return _OLLAMA_EP_CACHE[host]
    try:
        r = requests.get(f'{host}/v1/models', timeout=5)
        ep = 'v1' if r.status_code == 200 else 'api'
    except requests.RequestException:
        ep = 'api'
    _OLLAMA_EP_CACHE[host] = ep
    return ep


def _normalize(raw_calls: list) -> list:
    """
    统一 tool_calls 结构。
    关键：旧版 /api/chat 的 arguments 是 dict，必须 json.dumps，
          否则 harness 里 json.loads 会抛 TypeError
    """
    out = []
    for i, c in enumerate(raw_calls or []):
        fn = c.get('function', {})
        args = fn.get('arguments', {})
        out.append({
            'id': c.get('id') or f'call_{i}',
            'function': {
                'name': fn.get('name'),
                'arguments': args if isinstance(args, str)
                else json.dumps(args, ensure_ascii=False),
            }
        })
    return out


class LLMService:
    """单例，由 app lifespan 注入配置"""

    def __init__(self, provider: str = None, timeout: int = 180):
        self.cfg = LLMConfig_
        self.provider = provider or self.cfg.llm_provider
        self.timeout = timeout

    # ---------- Ollama ----------
    def _ollama_stream(self, messages, tools):
        host = self.cfg.ollama_host
        model = self.cfg.ollama_model
        ep = _detect_ollama_endpoint(host)
        payload = {'model': model, 'messages': messages, 'stream': True,
                'options': {'temperature': AgentConfig_.agent_temperature}}
        if tools:
            payload['tools'] = tools

        # ---- /v1：OpenAI 兼容 SSE，data: 逐行 ----
        if ep == 'v1':
            r = requests.post(f'{host}/v1/chat/completions', json=payload,
                            stream=True, timeout=self.timeout)
            r.raise_for_status()
            for line in r.iter_lines(decode_unicode=False):
                line = (line or b'').decode('utf-8', errors='replace').strip()
                if not line.startswith('data:'):
                    continue
                data = line[len('data:'):].strip()
                if not data or data == '[DONE]':
                    continue
                try:
                    item = json.loads(data)
                except json.JSONDecodeError:
                    continue                                # ← 坏行跳过，不中断
                if not item.get('choices'):
                    continue
                delta = item['choices'][0].get('delta', {})
                if delta.get('content'):
                    yield {"type": "content", "text": delta['content']}
                for tc in (delta.get('tool_calls') or []):
                    yield {
                        "type": "tool_call",
                        "index": tc.get('index', 0),
                        "id": tc.get('id'),
                        "name": (tc.get('function') or {}).get('name'),
                        "arguments": (tc.get('function') or {}).get('arguments'),
                    }
            return

        # ---- /api：NDJSON 逐行 ----
        r = requests.post(f'{host}/api/chat', json=payload,
                        stream=True, timeout=self.timeout)
        r.raise_for_status()
        tc_idx = 0
        for line in r.iter_lines(decode_unicode=False):
            if not line:
                continue
            line = line.decode("utf-8", errors="replace").strip()
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue                                    # ← 坏行跳过，不中断
            msg = item.get('message', {})
            if msg.get('content'):
                yield {"type": "content", "text": msg['content']}
            for tc in (msg.get('tool_calls') or []):
                fn = tc.get('function', {})
                args = fn.get('arguments', {})
                yield {
                    "type": "tool_call",
                    "index": tc_idx,
                    "id": tc.get('id') or f'call_{tc_idx}',
                    "name": fn.get('name'),
                    "arguments": args if isinstance(args, str)
                    else json.dumps(args, ensure_ascii=False),
                    "_complete": True,
                }
                tc_idx += 1


    # ---------- 国内 API（OpenAI 兼容）----------
    def _openai_stream(self, messages, tools):
        from openai import OpenAI
        client = OpenAI(api_key=self.cfg.api_key, base_url=self.cfg.api_base_url or None)
        kw = {'model': self.cfg.api_model, 'messages': messages,
            'temperature': 0, 'stream': True}
        if tools:
            kw['tools'] = tools

        stream = client.chat.completions.create(**kw)
        for chunk in stream:
            if not chunk.choices:
                continue                     # 末尾的 usage chunk choices 为空，跳过
            delta = chunk.choices[0].delta
            if delta.content:
                yield {"type": "content", "text": delta.content}
            for tc in (delta.tool_calls or []):
                yield {
                    "type": "tool_call",
                    "index": tc.index,
                    "id": tc.id if tc.id else None,              # 仅首个片段有
                    "name": tc.function.name if tc.function else None,
                    "arguments": tc.function.arguments if tc.function else None,  # 增量片段
                }

    
    def chat_stream(self, messages, tools=None):
        """流式版 chat()：按 provider 分发，产出结构化事件。
        事件协议（供 AgentHarness.run_stream 消费）：
        {"type":"content","text":str}                —— 增量文本
        {"type":"tool_call","index":int,"id":str|None,
        "name":str|None,"arguments":str|None}        —— 工具调用增量/片段
        """
        if self.provider == 'ollama':
            return self._ollama_stream(messages, tools)
        return self._openai_stream(messages, tools)


    # ---------- embedding ----------
    def embed(self, texts):
        r = requests.post(f"{self.cfg.ollama_host}/api/embed",
                          json={'model': self.cfg.embed_model, 'input': texts},
                          timeout=120)
        r.raise_for_status()
        return r.json()['embeddings']

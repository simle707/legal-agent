# -*- coding: utf-8 -*-
"""
对话业务层 —— 编排：记忆注入 -> Agent 工具调用 -> 回写记忆
是 service 层的核心，controller 只做参数转发
"""
import json
from typing import Optional

from module_law.service.agent.registry import ToolRegistry
from module_law.service.agent.harness import AgentHarness, verify_numbers
from module_law.service.agent.llm_service import LLMService
from module_law.service.agent.memory_service import MemoryService
from module_law.service.agent.tools import registry as default_registry
from core.rag_engine import get_engine
from module_law.service.agent.citation_guard import CitationGuard


class ChatService:

    _instance = None          # 单例：短期/长期记忆必须跨请求保留

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._inited = False
        return cls._instance

    def __init__(self):
        if getattr(self, '_inited', False):
            return
        self.llm = LLMService()
        self.memory = MemoryService()
        self.registry = default_registry
        self.harness = AgentHarness(
            llm_fn_stream=self.llm.chat_stream,
            registry=self.registry,
        )
        self._inited = True

    # ---------- 查询改写：记忆的主要用途 ----------
    def rewrite_query(self, question: str, history: list, slots: dict) -> str:
        """指代表达（"那我能拿多少"）必须消解后才能检索，否则召回全是垃圾"""
        if not history:
            return question
        if not any(w in question for w in ['那', '这个', '它', '他', '这种情况', '上面', '上述']):
            return question
        ctx = "\n".join(f"{h['role']}: {h['content']}" for h in history[-4:])
        prompt = (f'把用户最新提问改写成独立完整、可直接检索法律条文的问题。\n'
                  f'补全指代，保留关键事实，不要回答问题，只输出改写后的问题。\n\n'
                  f'已知事实：{json.dumps(slots, ensure_ascii=False)}\n'
                  f'历史：\n{ctx}\n\n'
                  f'最新提问：{question}\n\n改写后：')
        try:
            resp = self.llm.chat([{'role': 'user', 'content': prompt}], None)
            return (resp.get('content') or question).strip() or question
        except Exception as e:
            print(f'[chat] 查询改写失败，用原句: {e}')
            return question

    # ---------- 降级：不走 Agent，直接 RAG + 生成 ----------
    def _fallback(self, question: str, slots: dict) -> dict:
        engine = get_engine()
        context = engine.as_context(question, 5)
        refs = [a.article_label or f'第{a.article_no}条'
                for a, _s in engine.search(question, 5)]
        prompt = (f'你是劳动法咨询助手。只依据下列法条原文作答，禁止编造。\n'
                  f'法条中没有的依据，必须说明"法条未明确规定"。\n\n'
                  f'【法条原文】\n{context}\n\n'
                  f'【用户问题】{question}\n\n'
                  f'请回答并标注法条编号：')
        try:
            resp = self.llm.chat([{'role': 'user', 'content': prompt}], None)
            return {'answer': resp.get('content'), 'trace': [], 'refs': refs,
                    'warning': '未使用工具调用（降级模式）'}
        except Exception as e:
            return {'answer': None, 'trace': [], 'refs': refs,
                    'warning': f'大模型不可用: {e}'}

    # ---------- 主流程 ----------
    def chat(self, session_id: str, user_id: str, question: str,
             use_agent: bool = True, slots: dict = None) -> dict:
        # ① 取记忆
        history = self.memory.get_history(session_id)
        profile = self.memory.get_profile(user_id)
        if slots:
            profile.update(slots)

        # ② 抽取本轮事实 -> 回写长期记忆
        self.memory.extract_slots(question, llm_fn=self.llm.chat, profile=profile)
        known = profile.to_dict()

        # ③ 消解指代
        query = self.rewrite_query(question, history, known)

        # ④ Agent 或降级
        if use_agent:
            try:
                result = self.harness.run(questions=query, slots_hint=known,
                                          history=history[-4:])
            except Exception as e:
                result = self._fallback(query, known)
                result['warning'] = f'{result.get("warning", "")} | {e}'.strip(' |')
        else:
            result = self._fallback(query, known)

        # ⑤ 数字校验：回答里的金额必须能在工具结果里找到
        # if result.get('answer'):
        #     tool_outputs = [t for t in result.get('trace', []) if t.get('ok')]
        #     if tool_outputs and not verify_numbers(result['answer'], tool_outputs):
        #         result['warning'] = (result.get('warning', '') +
        #                              ' | 回答中出现无法追溯的金额，请核对').strip(' |')

        if result.get('answer'):
            retrieved, tool_out = [], []
            for t in result.get('trace', []):
                if not t.get('ok'):
                    continue
                if t.get('tool') == 'search_law' and isinstance(t.get('result'), dict):
                    retrieved.extend(t['result'].get('articles', []))
                else:
                    tool_out.append(t.get('result'))

        guard = CitationGuard(retrieved, tool_out)
        report  = guard.check(result['answer'])
        result['citation'] = report
        if not report['pass']:
            result['answer'], _ = guard.enforce(result['answer'], strategy='mark')
            result['warning'] = (result.get('warning', '') + ' | ' + report['summary']).strip(' |')

        # ⑥ 回写短期记忆
        self.memory.append_turn(session_id, 'user', question)
        if result.get('answer'):
            self.memory.append_turn(session_id, 'assistant', result['answer'])

        result['slots'] = known
        result['mode'] = get_engine().mode
        if not result.get('refs'):
            result['refs'] = [t['args'].get('query')
                              for t in result.get('trace', []) if t.get('tool') == 'search_law']
            result['refs'] = [r for r in result['refs'] if r]
        return result

    def _fallback_stream(self, question: str, slots: dict):
        """降级路径流式版：RAG 检索（静默）→ LLM 逐 chunk 生成"""
        engine = get_engine()
        context = engine.as_context(question, 5)
        refs = [a.article_label or f'第{a.article_no}条'
                for a, _s in engine.search(question, 5)]
        prompt = (f'你是劳动法咨询助手。只依据下列法条原文作答，禁止编造。\n'
                f'法条中没有的依据，必须说明"法条未明确规定"。\n\n'
                f'【法条原文】\n{context}\n\n'
                f'【用户问题】{question}\n\n'
                f'请回答并标注法条编号：')
        try:
            for delta in self.llm.chat_stream([{'role': 'user', 'content': prompt}], None):
                if delta:
                    yield {"type": "delta", "content": delta}
        except Exception as e:
            yield {"type": "delta", "content": f"（大模型不可用: {e}）"}
        yield {"type": "done", "trace": [], "refs": refs,
            "warning": "未使用工具调用（降级模式）"}


    def chat_stream(self, session_id: str, user_id: str, question: str,
                use_agent: bool = True, slots: dict = None):
        """
        流式版 chat()：编排阶段静默（记忆/改写/工具调用不 yield）
        只在 LLM 生成最终回答时逐 chunk yield，首 token 到即出字。
        事件协议（SSE 的 data 载荷）：start → delta × N → done
        """
        # ① 取记忆 —— 与 chat() 完全一致
        history = self.memory.get_history(session_id)
        profile = self.memory.get_profile(user_id)
        if slots:
            profile.update(slots)

        # ② 抽取本轮事实 -> 回写长期记忆（静默）
        self.memory.extract_slots(question, llm_fn=self.llm.chat_stream, profile=profile)
        known = profile.to_dict()

        # ③ 消解指代（静默）
        query = self.rewrite_query(question, history, known)

        # 前端可据此先亮"思考中"
        yield {"type": "start", "mode": get_engine().mode}

        answer, trace, warning, refs = "", [], "", []

        # ④ Agent 或降级：最终生成均走流式
        if use_agent:
            try:
                for evt in self.harness.run_stream(
                    questions=query, slots_hint=known, history=history[-4:]
                ):
                    if evt.get("type") == "delta":
                        answer += evt["content"]
                        yield {"type": "delta", "content": evt["content"]}
                    elif evt.get("type") == "done":
                        trace = evt.get("trace", [])
                        warning = evt.get("warning", "")
                        refs = evt.get("refs", [])
            except Exception as e:
                warning = f'{warning} | {e}'.strip(' |')
                for evt in self._fallback_stream(query, known):
                    if evt.get("type") == "delta":
                        answer += evt["content"]
                        yield {"type": "delta", "content": evt["content"]}
                    elif evt.get("type") == "done":
                        refs = evt.get("refs", [])
                        warning = f'{warning} | {evt.get("warning", "")}'.strip(' |')
        else:
            for evt in self._fallback_stream(query, known):
                if evt.get("type") == "delta":
                    answer += evt["content"]
                    yield {"type": "delta", "content": evt["content"]}
                elif evt.get("type") == "done":
                    refs = evt.get("refs", [])
                    warning = evt.get("warning", "")

        # ⑤ 数字校验：流式内容已发出，校验结果只能并入 warning（无法撤回已显示的文本）
        if answer and trace:
            tool_outputs = [t for t in trace if t.get('ok')]
            if tool_outputs and not verify_numbers(answer, tool_outputs):
                warning = (warning + ' | 回答中出现无法追溯的金额，请核对').strip(' |')

        # ⑥ 回写短期记忆：流结束后用完整文本，时机后移
        self.memory.append_turn(session_id, 'user', question)
        if answer:
            self.memory.append_turn(session_id, 'assistant', answer)

        # ⑦ 收尾事件：字段与 chat() 的 result 对齐，前端兜底逻辑无需改
        yield {
            "type": "done",
            "answer": answer,
            "reply": answer,          # 兼容前端读 data.reply
            "trace": trace,
            "refs": refs,
            "citations": refs,        # 兼容前端读 data.citations
            "attachments": [],
            "warning": warning,
            "slots": known,
            "mode": get_engine().mode,
        }



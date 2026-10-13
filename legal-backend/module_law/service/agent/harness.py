import json
from typing import Optional, Callable
from config.env import AgentConfig_
from module_law.service.agent.registry import ToolRegistry
from exceptions.handler import ServiceException


DEFAULT_SYSTEM = """你是劳动法咨询助手，必须遵守：
1. 涉及具体金额一律调用 calc_compensation 计算，禁止自己算或估算
2. 引用法条必须调用 search_law 取原文，禁止凭记忆写条文
3. 每个结论标注法条编号
4. 参数缺失时先向用户追问，禁止编造参数值
5. 回答不构成法律意见，复杂情况建议咨询律师
"""


class AgentHarness:
    """
    LLM 说要调工具 -> 执行 -> 把结果塞回 messages -> 再问 LLM，
    直到不再要调工具或达到 max_steps。
    """

    def __init__(self, llm_fn_stream: Callable, registry: ToolRegistry, 
                 max_steps: int = None, system_prompt: str = None):
        self.llm_stream = llm_fn_stream
        self.registry = registry
        self.max_steps = max_steps or AgentConfig_.agent_max_steps
        self.system_prompt = system_prompt or DEFAULT_SYSTEM

    def run_stream(self, questions: str, slots_hint: dict = None,
               history: list = None):
        """run() 的流式版：工具调用阶段静默执行，最后一次生成（无 tool_calls）逐 chunk yield。
        事件协议：{"type":"delta","content":str} × N → {"type":"done","trace":[...],"warning":str}
        """
        if not getattr(self, 'llm_stream', None):
            raise ServiceException('AgentHarness 未配置 llm_fn_stream，无法流式生成', code=500)

        sys_content = self.system_prompt
        if slots_hint:
            sys_content += f"\n\n已知用户事实: {json.dumps(slots_hint, ensure_ascii=False)}"

        messages = [{'role': 'system', 'content': sys_content}]
        for h in (history or []):
            messages.append({'role': h.get('role'), 'content': h.get('content')})
        messages.append({'role': 'user', 'content': questions})

        trace = []

        for step in range(self.max_steps):
            # 与 run() 的唯一核心差异：流式调用，边收 content 边重组 tool_calls
            content_buf = []
            tc_buf = {}          # index -> {'id','name','arguments':[片段]}
            try:
                for evt in self.llm_stream(messages, self.registry.schemas()):
                    if evt.get('type') == 'content' and evt.get('text'):
                        content_buf.append(evt['text'])
                    elif evt.get('type') == 'tool_call':
                        idx = evt['index']
                        slot = tc_buf.setdefault(idx, {'id': '', 'name': '', 'arguments': []})
                        if evt.get('id'):
                            slot['id'] = evt['id']
                        elif not slot['id']:
                            slot['id'] = f'call_{idx}'
                        if evt.get('name'):
                            slot['name'] = evt['name']
                        if evt.get('arguments'):
                            slot['arguments'].append(evt['arguments'])
            except Exception as e:
                # 流已开始，不能 raise（连接中断）；把错误作为 done 事件带出
                yield {"type": "delta", "content": f"（回答中断: {e}）"}
                yield {"type": "done", "trace": trace, "warning": f'大模型调用失败：{e}'}
                return

            # 把流式增量重组为 run() 同构的 calls
            calls = []
            for idx in sorted(tc_buf):
                slot = tc_buf[idx]
                calls.append({
                    'id': slot['id'],
                    'type': 'function',
                    'function': {
                        'name': slot['name'],
                        'arguments': ''.join(slot['arguments']),
                    },
                })

            if not calls:
                # ← 这就是最终回答：把已收到的文本逐 chunk 吐出去（真流式）
                for part in content_buf:
                    yield {"type": "delta", "content": part}
                yield {"type": "done", "trace": trace}
                return

            # 有工具调用：静默执行（不 yield 给前端），逻辑与 run() 完全一致
            messages.append({
                'role': 'assistant',
                'content': ''.join(content_buf) or '',
                'tool_calls': calls,
            })

            for c in calls:
                name = c['function']['name']
                try:
                    args = json.loads(c['function']['arguments'] or '{}')
                except json.JSONDecodeError as e:
                    trace.append({'step': step, 'tool': name, 'args': {},
                                'ok': False, 'error': f'参数解析失败: {e}'})
                    messages.append({
                        'role': 'tool', 'tool_call_id': c['id'], 'name': name,
                        'content': json.dumps({'error': '参数格式错误'}, ensure_ascii=False),
                    })
                    continue

                try:
                    result = self.registry.execute(name, args)
                    ok, err = True, None
                except Exception as e:
                    result = {'error': str(e)}
                    ok, err = False, str(e)

                trace.append({'step': step, 'tool': name, 'args': args,
                            'ok': ok, 'err': err})
                messages.append({
                    'role': 'tool', 'tool_call_id': c['id'], 'name': name,
                    'content': json.dumps(result, ensure_ascii=False, default=str),
                })

        yield {"type": "done", "trace": trace,
            "warning": f'达到最大步数 {self.max_steps}, 未形成最终结论'}

def verify_numbers(answer, str, tool_results: list) -> bool:
    """回答里出现的金额必须能在工具返回值里找到——防幻觉最后一道闸"""
    import re 
    if not answer:
        return True
    nums = set(re.findall(r'(\d+(?:\.\d+)?)\s*(?:元|万元)'), answer)
    if not nums:
        return True
    allowed = set(re.findall(r'(\d+(?:\.\d+)?)',
                             json.dumps(tool_results, ensure_ascii=False, default=str)))
    return all(n in allowed for n in nums)         
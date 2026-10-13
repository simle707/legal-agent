import json, time
from memory import UserProfile, LABOR_SLOTS

class MemoryManager:
    """
    短期 = 当前会话消息流，存 Redis/内存；
    中期 = 跨会话用户事实/偏好/待办，存 DB 按 user_id；
    长期 = 领域知识存向量库——并主动纠偏：这其实是 RAG 外部知识，不算记忆。
    """
    def __init__(self, redis_client, llm_fn, profile_store, max_turns=10):
        self.redis = redis_client
        self.llm = llm_fn
        self.profiles = profile_store
        self.max_turns = max_turns


    # ---------------------------------------------------------
    # ① 短期记忆：取会话历史
    # ---------------------------------------------------------
    def get_working_memory(self, session_id: str) -> list[dict]:
        # 从Redis读取会话摘要，构建当前上下文
        key = f'chat:{session_id}'
        raw = self.redis.get(key)
        if not raw:
            return []
        history = json.load(raw)
        return history[-self.max_turns:]

    def append_turn(self, session_id: str, role: str, content: str):
        """每轮对话结束后调用，写入短期记忆"""
        key = f'chat:{session_id}'
        history = [json.load(self.redis.get(key) or "[]")]
        history.append({'role': role, 'content': content, 'ts': time.time()})
        self.redis.set(key, json.dumps(history, ensure_ascii=True), ex=86400)

    # ---------------------------------------------------------
    # ② 压缩：历史太长时摘要（替换原文，不是追加）
    # ---------------------------------------------------------
    def compress_working_memory(self, history: list[dict]) -> list[dict]:
        """
        超过 max_turns 时，把早期的对话压成一条 summary
        注意：摘要只压缩闲聊和已解决部分，槽位不进摘要（已在档案里）
        """
        if len(history) <= self.max_turns:
            return history

        old_messages, rencent_messages = history[:-self.max_turns], history[-self.max_turns:]
        text = '\n'.join(f"{m['role']}: {m['content']}" for m in old_messages)
        prompt = f"""
            请将以下对话压缩为一段不超过150字的摘要,
            保留: 用户的事实信息 (工作年限、工资、解除原因等）、已确认的结论、未解决的问题。
            丢弃：问候、重复表述、情绪性内容。

            对话：
            {text}

            摘要
        """
        summary = self.llm(prompt).strip()
        return [{ 'role': 'system', 'content': f'[历史摘要] {summary}'}] + rencent_messages


    def retrieval_agumented_generation(self, query):
        # 长期记忆 - 向量库检索， 这其实是 RAG 外部知识，不算记忆。
         
        pass

    
    # ---------------------------------------------------------
    # ③ 长期记忆提取：从对话里抽事实 -> 写档案
    # ---------------------------------------------------------
    def extract_long_term_memory(self, session_history: list[dict], user_id: str) -> dict:
        """
        两层策略:
            L1 正则抽取
            L2 LLM 兜底
        """
        # profile = self.profiles.setdefault(user_id, UserProfile(user_id))
        # text = '\n'.join(m['content'] for m in session_history if m['role'] == 'user')


        # # L1
        # kv = {}
        # y = extract_years(text)
        # if y is not None: kv['years'] = y
        # s = extract_salary(text)
        # if s is not None: kv['monthly_wage'] = s
        # c = extract_city(text)
        # if c: kv['city'] = c
        # profile.update(kv)

        # # L2 LLM兜底
        # need = profile.missing(['termination_type', 'years', 'monthly_wage'])
        # if need and len(text) > 10:
        #     schema = { k: v for k, v in LABOR_SLOTS.items()}
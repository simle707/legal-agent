import time

LABOR_SLOTS = {
    "years":       "在本单位工作年限（年），用于算 N",
    "monthly_wage":"解除前12个月平均工资（元）",
    "city":        "工作地，用于查当地社平工资/最低工资",
    "termination_type": "解除类型：协商/过失性/无过失/违法/裁员/合同终止",
    "notice_days": "是否提前30天通知（影响 +1）",
    "probation":   "是否试用期",
    "contract_signed": "是否签书面合同",
    "annual_leave_days": "未休年假天数",
}


"""
为什么用槽位不用向量：
用户说"我干了3年"，下次问"能赔多少"，槽位直接给出 years=3.0 
供计算器使用；向量召回只会给你一句"我在公司干了3年"的文本，还得让 LLM 再抽一次，多一次幻觉机会。
"""
class UserProfile:
    """长期记忆: 一个用户的法律事实档案"""
    def __init__(self, user_id):
        self.user_id = user_id
        self.slots: dict = {}
        self.updated_at: dict = {}

    def update(self, kv: dict):
        for k, v in kv.items():
            if v is not None:
                self.slots[k] = v
                self.updated_at[k] = time.time()

    def missing(self, required: list[str]) -> list[str]:
        """返回还缺哪些槽位 -- 用于决定该回答还是反问"""
        return [k for k in required if k not in self.slots]


    def to_dict(self):
        return {
            'user_id': self.user_id,
            'slots': self.slots,
            'update_at': self.updated_at
        }
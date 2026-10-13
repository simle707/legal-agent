# -*- coding: utf-8 -*-
"""赔偿计算业务层 —— 纯确定性计算，绝不让 LLM 参与"""
from typing import Optional

# 类型: (法定标准, 倍数, 是否可能有+1代通知金, 法条依据)
TYPE_RULE = {
    '协商解除':      ('N',  1, 0, '第三十六条'),
    '劳动者被迫解除': ('N',  1, 0, '第三十八条'),
    '无过失性辞退':   ('N',  1, 1, '第四十条'),
    '经济性裁员':     ('N',  1, 0, '第四十一条'),
    '合同期满终止':   ('N',  1, 0, '第四十四条第一项'),
    '违法解除':      ('2N', 2, 0, '第八十七条'),
    '过失性辞退':     ('0',  0, 0, '第三十九条'),
    '非全日制终止':   ('0',  0, 0, '第七十一条'),
}


class CalculatorService:

    @classmethod
    def calc_months(cls, years: float) -> float:
        """
        第四十七条分段规则：
          满一年 -> 1个月
          剩余六个月以上不满一年 -> 按一年算（+1）
          剩余不满六个月 -> +0.5
        注意：不能用 round(years)，3年5个月会被算成3个月
        """
        full = int(years)
        frac = years - full
        if frac >= 0.5:
            return float(full + 1)
        if frac > 0:
            return full + 0.5
        return float(full)

    @classmethod
    def calc(cls, years: float, monthly_wage: float, termination_type: str,
             social_avg_wage: Optional[float] = None,
             notice_given: bool = True) -> dict:
        if termination_type not in TYPE_RULE:
            return {'error': f'未知解除类型: {termination_type}',
                    'supported': list(TYPE_RULE)}

        name, mult, plus1, basis = TYPE_RULE[termination_type]
        months = cls.calc_months(years)
        wage = float(monthly_wage)

        # 第四十七条第二款：超社平三倍则按三倍计，且年限封顶12年
        capped_wage = capped_year = False
        if social_avg_wage:
            tri = social_avg_wage * 3
            if wage > tri:
                wage = tri
                capped_wage = True
                if years > 12:
                    months = 12.0
                    capped_year = True

        base = months * wage
        total = base * mult + (wage * plus1 if not notice_given else 0.0)

        return {
            '解除类型': termination_type,
            '法定标准': name,
            '法条依据': basis,
            '工作年限': years,
            '计发月数': months,
            '月工资计算基数': round(wage, 2),
            '经济补偿N': round(base, 2),
            '应得总额': round(total, 2),
            '代通知金': round(wage, 2) if (plus1 and not notice_given) else 0,
            '触及三倍封顶': capped_wage,
            '触及12年封顶': capped_year,
            '需核对社平工资': social_avg_wage is None,
        }

    @classmethod
    def supported_types(cls) -> list:
        return list(TYPE_RULE)

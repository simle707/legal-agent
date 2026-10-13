from typing import Literal, Optional
from module_law.service.agent.registry import ToolRegistry
from core.rag_engine import get_engine

registry = ToolRegistry()


@registry.register
def search_law(query: str, top_k: int = 5) -> dict:
    """检索劳动法条文原文。用户问权利义务、法律依据、某条规定了什么时调用。
    :param query: 完整独立的检索问题，不要使用代词
    :param top_k: 返回条数
    """
    engine = get_engine()
    hits = engine.search(query, top_k)
    return {'total': len(hits), 'articles': [{
        'article_no': a.article_no,
        'article_label': a.article_label,
        'chapter': a.chapter,
        'text': a.full_text,
    } for a, _s in hits]}


@registry.register
def calc_compensation(years: float, monthly_wage: float,
                      termination_type: Literal['协商解除', '劳动者被迫解除', '无过失性辞退',
                                                '经济性裁员', '合同期满终止', '违法解除',
                                                '过失性辞退', '非全日制终止'],
                      social_avg_wage: Optional[float] = None,
                      notice_given: bool = True) -> dict:
    """计算经济补偿金或赔偿金。用户问能拿多少钱、赔偿多少时调用。
    :param years: 在本单位工作年限，3年5个月填 3.42
    :param monthly_wage: 解除前12个月平均工资，单位元
    :param termination_type: 解除类型
    :param social_avg_wage: 当地上年度职工月平均工资，用于三倍封顶判断，可省略
    :param notice_given: 是否提前30天书面通知，未通知则加1个月代通知金
    """
    from module_law.service.calculator_service import CalculatorService
    return CalculatorService.calc(years=years, monthly_wage=monthly_wage,
                                  termination_type=termination_type,
                                  social_avg_wage=social_avg_wage,
                                  notice_given=notice_given)


@registry.register
def get_article(article_no: int) -> dict:
    """按条号精确取一条法条原文。用户明确说出"第X条"时优先用这个。
    :param article_no: 条号，如 47
    """
    engine = get_engine()
    idx = engine.no2idx.get(article_no)
    if idx is None:
        return {'error': f'未找到第{article_no}条'}
    a = engine.articles[idx]
    return {'article_no': a.article_no, 'article_label': a.article_label,
            'chapter': a.chapter, 'text': a.full_text}
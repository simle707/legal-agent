# -*- coding: utf-8 -*-
"""法规视图对象（VO）—— 请求/响应模型，对应 ruoyi 的 entity/vo"""
from typing import Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel


class _CamelModel(BaseModel):
    """ruoyi 前端是 camelCase，后端 snake_case，统一在这里转换"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True,
                              from_attributes=True)


# ==================== 法条查询 ====================
class LawArticleModel(_CamelModel):
    id: Optional[int] = None
    law_name: Optional[str] = None
    article_no: Optional[int] = None
    article_label: Optional[str] = None
    chapter: Optional[str] = None
    full_text: Optional[str] = None


class LawSearchModel(_CamelModel):
    """检索请求体"""
    query: str = Field(..., description='检索问题')
    top_k: int = Field(5, ge=1, le=20, description='返回条数')


class LawArticleHitModel(_CamelModel):
    """检索结果项"""
    article_no: Optional[int] = None
    article_label: Optional[str] = None
    chapter: Optional[str] = None
    full_text: Optional[str] = None
    score: float = 0.0


class LawPageQueryModel(_CamelModel):
    """分页查询法条"""
    law_name: Optional[str] = None
    article_no: Optional[int] = None
    page_num: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)

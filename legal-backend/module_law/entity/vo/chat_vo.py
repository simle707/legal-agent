# -*- coding: utf-8 -*-
"""对话/计算器视图对象"""
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True,
                              from_attributes=True)


# ==================== 赔偿计算器 ====================
class CalcCompensationModel(_CamelModel):
    years: float = Field(..., gt=0, le=50, description='工作年限，3年5个月填3.42')
    monthly_wage: float = Field(..., gt=0, description='解除前12个月平均工资')
    termination_type: str = Field(..., description='解除类型')
    social_avg_wage: Optional[float] = Field(None, description='当地上年度职工月平均工资')
    notice_given: bool = Field(True, description='是否提前30天通知')


class CalcResultModel(_CamelModel):
    解除类型: Optional[str] = None
    法定标准: Optional[str] = None
    法条依据: Optional[str] = None
    工作年限: Optional[float] = None
    计发月数: Optional[float] = None
    月工资计算基数: Optional[float] = None
    经济补偿N: Optional[float] = None
    应得总额: Optional[float] = None
    代通知金: Optional[float] = None
    触及三倍封顶: Optional[bool] = None
    触及12年封顶: Optional[bool] = None
    需核对社平工资: Optional[bool] = None


# ==================== 对话 ====================
class ChatMessageModel(_CamelModel):
    role: str
    content: str


class ChatRequestModel(_CamelModel):
    session_id: str = Field(..., description='会话ID')
    user_id: str = Field('anonymous', description='用户ID')
    question: str = Field(..., description='用户提问')
    use_agent: bool = Field(True, description='是否走 Agent 工具调用')
    slots: Optional[Dict[str, Any]] = Field(None, description='已知用户事实')


class ToolCallTraceModel(_CamelModel):
    step: int
    tool: str
    args: Dict[str, Any]
    ok: bool = True
    error: Optional[str] = None


class ChatResponseModel(_CamelModel):
    answer: Optional[str] = None
    trace: List[ToolCallTraceModel] = []
    slots: Dict[str, Any] = {}
    refs: List[str] = []
    warning: Optional[str] = None
    mode: Optional[str] = None

# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from config.get_db import get_db
from utils.response_util import ResponseUtil
from module_law.entity.vo.chat_vo import CalcCompensationModel
from module_law.service.calculator_service import CalculatorService

calculator_controller = APIRouter(prefix='/calc', tags=['赔偿计算器'])


@calculator_controller.post('/compensation', summary='经济补偿金/赔偿金计算')
def compensation(body: CalcCompensationModel, session: Session = Depends(get_db)):
    data = CalculatorService.calc(
        years=body.years,
        monthly_wage=body.monthly_wage,
        termination_type=body.termination_type,
        social_avg_wage=body.social_avg_wage,
        notice_given=body.notice_given,
    )
    if 'error' in data:
        return ResponseUtil.failure(msg=data['error'], code=400)
    return ResponseUtil.success(data=data)

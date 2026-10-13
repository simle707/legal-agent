# -*- coding: utf-8 -*-
"""统一响应封装，对齐 ruoyi 的 AjaxResponse/TableResponse"""
import datetime
import json
from typing import Any, Optional
from fastapi.responses import JSONResponse


class ResponseUtil:

    @staticmethod
    def _body(code: int, msg: str, success: bool, data: Any):
        return {
            'code': code,
            'msg': msg,
            'success': success,
            'time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data': data,
        }

    @classmethod
    def success(cls, msg: str = '操作成功', data: Any = None) -> dict:
        return cls._body(200, msg, True, data)

    @classmethod
    def failure(cls, msg: str = '操作失败', data: Any = None, code: int = 500) -> dict:
        return cls._body(code, msg, False, data)

    @classmethod
    def unauthorized(cls, msg: str = '认证失败') -> dict:
        return cls._body(401, msg, False, None)

    @classmethod
    def forbidden(cls, msg: str = '没有访问权限') -> dict:
        return cls._body(403, msg, False, None)

    @classmethod
    def not_found(cls, msg: str = '资源不存在') -> dict:
        return cls._body(404, msg, False, None)

    @classmethod
    def ok(cls, msg: str = '操作成功', data: Any = None) -> JSONResponse:
        return JSONResponse(content=cls.success(msg, data))

    @classmethod
    def fail(cls, msg: str = '操作失败', data: Any = None, code: int = 500) -> JSONResponse:
        return JSONResponse(content=cls.failure(msg, data, code))

    @classmethod
    def table(cls, rows: list, total: int, msg: str = '查询成功') -> dict:
        """ruoyi 的 TableDataInfo：data 里放 rows/total"""
        return cls.success(msg, {'rows': rows, 'total': total})

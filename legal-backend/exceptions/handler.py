# -*- coding: utf-8 -*-
"""全局异常处理"""
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from utils.response_util import ResponseUtil


class ServiceException(Exception):
    """业务异常，主动抛"""

    def __init__(self, msg: str = '业务处理失败', code: int = 500, data=None):
        self.msg = msg
        self.code = code
        self.data = data
        super().__init__(msg)


class ToolExecuteException(Exception):
    """Agent 工具执行异常，不中断整体流程，交给 harness 记录后继续"""


def register_exception_handlers(app):
    @app.exception_handler(ServiceException)
    async def _service_handler(request: Request, exc: ServiceException):
        return ResponseUtil.fail(exc.msg, exc.data, exc.code)

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request, exc: RequestValidationError):
        first = exc.errors()[0] if exc.errors() else {}
        loc = '.'.join(str(x) for x in first.get('loc', []))
        return ResponseUtil.fail(f'参数校验失败: {loc} {first.get("msg", "")}', code=400)

    @app.exception_handler(StarletteHTTPException)
    async def _http_handler(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404:
            return ResponseUtil.fail('接口不存在', code=404)
        if exc.status_code == 403:
            return ResponseUtil.fail('没有访问权限', code=403)
        return ResponseUtil.fail(str(exc.detail), code=exc.status_code)

    @app.exception_handler(Exception)
    async def _global_handler(request: Request, exc: Exception):
        return ResponseUtil.fail(f'服务器内部错误: {exc}')

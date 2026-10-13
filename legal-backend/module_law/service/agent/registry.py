# -*- coding: utf-8 -*-
"""
工具注册表（Harness 的第一块）
- @tool 装饰器：从类型注解 + docstring 自动生成 OpenAI JSON Schema
- 一处定义 = 一份 Schema + 一个可调用函数，避免手写 JSON 与实现脱节
"""
import inspect
import json
from typing import Callable, get_type_hints, Optional, get_origin, get_args


class ToolSpec:
    def __init__(self, name: str, description: str, func: Callable, schema: dict):
        self.name = name
        self.description = description
        self.func = func
        self.schema = schema

    def to_openai(self) -> dict:
        """OpenAI / 国内各家兼容格式"""
        return {
            'type': 'function',
            'function': {
                'name': self.name,
                'description': self.description,
                'parameters': self.schema,
            }
        }


_PY2JSON = {str: 'string', int: 'integer', float: 'number', bool: 'boolean',
            list: 'array', dict: 'object'}


def _json_type(anno):
    """python 类型 -> JSON Schema 类型；Optional[X] 解一层"""
    origin = get_origin(anno)
    if origin is Optional or (origin is not None and str(origin).startswith('typing.Union')):
        args = [a for a in get_args(anno) if a is not type(None)]
        if args:
            return _json_type(args[0])
    if origin in (list, tuple):
        return 'array'
    if origin is dict:
        return 'object'
    return _PY2JSON.get(anno, 'string')


class ToolRegistry:
    """工具容器：注册、导出 schema、执行"""

    def __init__(self):
        self._tools: dict[str, ToolSpec] = {}

    def register(self, func: Callable = None, *, name: str = None,
                 description: str = None, required: list = None):
        """
        用法一（推荐，自动推导）:
            @registry.register
            def search_law(query: str, top_k: int = 5) -> dict:
                '''检索劳动法条文'''
        用法二（显式）:
            @registry.register(name='xxx', description='xxx')
        """
        def deco(f: Callable):
            fn_name = name or f.__name__
            desc = description or (inspect.getdoc(f) or f.__name__).strip()
            schema = self._build_schema(f, required)
            self._tools[fn_name] = ToolSpec(fn_name, desc, f, schema)
            return f

        return deco(func) if func is not None else deco

    def _build_schema(self, f: Callable, required: list = None) -> dict:
        hints = get_type_hints(f)
        sig = inspect.signature(f)
        props, req = {}, []
        for pname, p in sig.parameters.items():
            if pname in ('self', 'cls'):
                continue
            anno = hints.get(pname, str)
            jt = _json_type(anno)
            item = {'type': jt}
            # enum：从类型注解 Literal 或参数的默认值类型猜测，这里支持显式 Literal
            origin = get_origin(anno)
            if str(origin).startswith('typing.Literal'):
                item['enum'] = list(get_args(anno))
            # 描述从 docstring 的 ":param xxx: ..." 里抠
            doc = inspect.getdoc(f) or ''
            for line in doc.splitlines():
                line = line.strip()
                if line.startswith(f':param {pname}:'):
                    item['description'] = line.split(':', 2)[-1].strip()
            props[pname] = item
            if required is not None:
                if pname in required:
                    req.append(pname)
            elif p.default is inspect.Parameter.empty:
                req.append(pname)
        return {'type': 'object', 'properties': props, 'required': req}

    def specs(self) -> list:
        return list(self._tools.values())

    def schemas(self) -> list:
        return [s.to_openai() for s in self._tools.values()]

    def get(self, name: str) -> Optional[ToolSpec]:
        return self._tools.get(name)

    def execute(self, name: str, args: dict):
        spec = self._tools.get(name)
        if spec is None:
            raise KeyError(f'未注册的工具: {name}')
        return spec.func(**args)

    def names(self) -> list:
        return list(self._tools.keys())

# -*- coding: utf-8 -*-
"""Redis 客户端；未启用时返回内存替代品，保证不阻塞开发"""
import json
from typing import Optional
from config.env import RedisConfig_


class _MemoryRedis:
    """内存版 Redis，接口只覆盖本项目用到的 get/set/delete"""

    def __init__(self):
        self._d = {}

    def get(self, k):
        return self._d.get(k)

    def set(self, k, v, ex=None):
        self._d[k] = v
        return True

    def delete(self, k):
        self._d.pop(k, None)
        return True

    def ping(self):
        return True


_redis = None


def get_redis():
    global _redis
    if _redis is None:
        if RedisConfig_.redis_enabled:
            try:
                import redis
                _redis = redis.Redis(
                    host=RedisConfig_.redis_host, port=RedisConfig_.redis_port,
                    db=RedisConfig_.redis_db, password=RedisConfig_.redis_password or None,
                    decode_responses=True)
                _redis.ping()
                print('[redis] 已连接')
            except Exception as e:
                print(f'[redis] 连接失败，降级内存模式: {e}')
                _redis = _MemoryRedis()
        else:
            print('[redis] 未启用，使用内存模式')
            _redis = _MemoryRedis()
    return _redis

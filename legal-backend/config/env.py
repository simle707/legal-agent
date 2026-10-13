# -*- coding: utf-8 -*-
"""配置：Pydantic BaseSettings + lru_cache，对应 ruoyi 的 config/env.py"""
from functools import lru_cache
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env.dev', env_file_encoding='utf-8',
                                      extra='ignore')
    app_env: str = 'dev'
    app_name: str = 'legal-backend'
    app_description: str = 'law asisstant'
    app_version: str = '0.0.1'
    app_host: str = '0.0.0.0'
    app_port: int = 8000
    app_root_path: str = '/dev-api'
    app_debug: bool = True


class DataBaseConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env.dev', env_file_encoding='utf-8',
                                      extra='ignore', env_prefix='')
    db_type: str = 'sqlite'
    db_host: str = '127.0.0.1'
    db_port: int = 5432
    db_user: str = 'postgres'
    db_password: str = 'postgres'
    db_name: str = 'law'
    sqlite_path: str = './law.db'

    @property
    def uri(self) -> str:
        if self.db_type == 'sqlite':
            return f'sqlite:///{self.sqlite_path}'
        return (f'postgresql+psycopg2://{self.db_user}:{self.db_password}'
                f'@{self.db_host}:{self.db_port}/{self.db_name}')


class RedisConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env.dev', env_file_encoding='utf-8',
                                      extra='ignore')
    redis_host: str = '127.0.0.1'
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ''
    redis_enabled: bool = False


class LLMConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env.dev', env_file_encoding='utf-8',
                                      extra='ignore')
    llm_provider: str = 'ollama'
    ollama_host: str = 'http://localhost:11434'
    ollama_model: str = 'qwen2.5:7b'
    embed_model: str = 'bge-m3'
    api_key: str = ''
    api_base_url: str = ''
    api_model: str = 'deepseek-chat'


class AgentConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env.dev', env_file_encoding='utf-8',
                                      extra='ignore')
    agent_max_steps: int = 5
    agent_temperature: float = 0.0
    memory_max_turns: int = 10


class GetConfig:
    """配置聚合入口，对应 ruoyi 的 GetConfig"""

    @staticmethod
    @lru_cache()
    def get_app_config() -> AppConfig:
        return AppConfig()

    @staticmethod
    @lru_cache()
    def get_database_config() -> DataBaseConfig:
        return DataBaseConfig()

    @staticmethod
    @lru_cache()
    def get_redis_config() -> RedisConfig:
        return RedisConfig()

    @staticmethod
    @lru_cache()
    def get_llm_config() -> LLMConfig:
        return LLMConfig()

    @staticmethod
    @lru_cache()
    def get_agent_config() -> AgentConfig:
        return AgentConfig()


# 模块级快捷访问
AppConfig_ = GetConfig.get_app_config()
DataBaseConfig_ = GetConfig.get_database_config()
RedisConfig_ = GetConfig.get_redis_config()
LLMConfig_ = GetConfig.get_llm_config()
AgentConfig_ = GetConfig.get_agent_config()

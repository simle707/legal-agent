# -*- coding: utf-8 -*-
"""数据库引擎与会话工厂"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from config.env import DataBaseConfig_

Base = declarative_base()

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        uri = DataBaseConfig_.uri
        kwargs = {'future': True, 'echo': False}
        if DataBaseConfig_.db_type == 'sqlite':
            kwargs['connect_args'] = {'check_same_thread': False}
        _engine = create_engine(uri, **kwargs)
    return _engine


def get_session_local():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), class_=Session,
                                     autocommit=False, autoflush=False)
    return _SessionLocal


def init_db():
    """建表（ruoyi 里通常在 lifespan 调）"""
    from module_law.entity.do.law_do import LawArticle  # noqa
    Base.metadata.create_all(bind=get_engine())

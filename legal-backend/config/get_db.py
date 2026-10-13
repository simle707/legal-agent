# -*- coding: utf-8 -*-
"""依赖注入：数据库会话"""
from typing import Annotated, Generator
from fastapi import Depends
from sqlalchemy.orm import Session
from config.database import get_session_local


def get_db() -> Generator[Session, None, None]:
    db = get_session_local()()
    try:
        yield db
    finally:
        db.close()


# ruoyi 风格：CurrentSession = Annotated[Session, Depends(get_db)]
CurrentSession = Annotated[Session, Depends(get_db)]

# -*- coding: utf-8 -*-
"""法条数据对象（DO）—— 映射已有 law.db 的 law_article 表"""
from sqlalchemy import Column, Integer, String, Text, LargeBinary
from config.database import Base


class LawArticle(Base):
    """
    注意：这是"已存在"的表，__tablename__ 必须与你 law.db 里的一致。
    字段保持与建库 SQL 一致，多的字段会自动忽略，缺失字段读出来是 None。
    """
    __tablename__ = 'law_article'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    law_name = Column(String(255), comment='法律名称')
    article_no = Column(Integer, comment='条号（阿拉伯数字）')
    article_label = Column(String(64), comment='第四十七条')
    chapter = Column(String(255), comment='所属章节')
    full_text = Column(Text, comment='条文原文')
    embed = Column(LargeBinary, comment='向量 BLOB')

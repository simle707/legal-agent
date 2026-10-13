# -*- coding: utf-8 -*-
"""法条数据访问层（DAO）—— 只做 SQL，不写业务"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from module_law.entity.do.law_do import LawArticle


class LawArticleDao:

    @classmethod
    def get_by_article_no(cls, db: Session, article_no: int) -> Optional[LawArticle]:
        return db.query(LawArticle).filter(LawArticle.article_no == article_no).first()

    @classmethod
    def list_all(cls, db: Session) -> List[LawArticle]:
        return db.query(LawArticle).order_by(LawArticle.article_no).all()

    @classmethod
    def list_by_condition(cls, db: Session, law_name: Optional[str] = None,
                          article_no: Optional[int] = None) -> List[LawArticle]:
        q = db.query(LawArticle)
        if law_name:
            q = q.filter(LawArticle.law_name.like(f'%{law_name}%'))
        if article_no is not None:
            q = q.filter(LawArticle.article_no == article_no)
        return q.order_by(LawArticle.article_no).all()

    @classmethod
    def count_all(cls, db: Session) -> int:
        return db.query(LawArticle).count()

# -*- coding: utf-8 -*-
"""法规检索业务层 —— 封装 RAG 引擎"""
from typing import List
from sqlalchemy.orm import Session
from core.rag_engine import get_engine
from module_law.dao.law_dao import LawArticleDao
from module_law.entity.vo.law_vo import LawArticleHitModel
from utils.page_util import PageUtil


class LawService:

    @classmethod
    def search(cls, query: str, top_k: int = 5) -> List[LawArticleHitModel]:
        engine = get_engine()
        hits = engine.search(query, top_k)
        return [LawArticleHitModel(article_no=a.article_no,
                                   article_label=a.article_label,
                                   chapter=a.chapter,
                                   full_text=a.full_text,
                                   score=round(float(s), 4))
                for a, s in hits]

    @classmethod
    def get_by_no(cls, db: Session, article_no: int):
        row = LawArticleDao.get_by_article_no(db, article_no)
        if row is None:
            return None
        return {'article_no': row.article_no, 'article_label': row.article_label,
                'chapter': row.chapter, 'full_text': row.full_text}

    @classmethod
    def page(cls, db: Session, law_name=None, article_no=None,
             page_num=1, page_size=10):
        rows = LawArticleDao.list_by_condition(db, law_name, article_no)
        data = [{'id': r.id, 'lawName': r.law_name, 'articleNo': r.article_no,
                 'articleLabel': r.article_label, 'chapter': r.chapter,
                 'fullText': r.full_text} for r in rows]
        return PageUtil.paginate(data, page_num, page_size), len(data)

    @classmethod
    def mode(cls) -> str:
        return get_engine().mode

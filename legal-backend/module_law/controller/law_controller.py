# module_law/controller/law_controller.py
from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session

from config.get_db import get_db
from utils.response_util import ResponseUtil
from utils.page_util import PageUtil
from module_law.service.law_service import LawService
from module_law.entity.vo.law_vo import LawSearchModel, LawPageQueryModel

law_controller = APIRouter(prefix='/law', tags=['法律法规'])


@law_controller.get('/search', summary='法条检索（混合召回）')
def search(query: str = Query(..., description='检索问题'),
           top_k: int = Query(5, ge=1, le=20),
           session: Session = Depends(get_db)):
    rows = LawService.search(query=query, top_k=top_k)
    return ResponseUtil.success(data=rows, msg=f'检索到 {len(rows)} 条')


@law_controller.get('/article/{article_no}', summary='按条号精确取法条')
def get_article(article_no: int, session: Session = Depends(get_db)):
    data = LawService.get_by_no(session, article_no)
    if not data:
        return ResponseUtil.not_found(msg=f'未找到第{article_no}条')
    return ResponseUtil.success(data=data)


@law_controller.get('/list', summary='法条分页列表')
def page_list(q: LawPageQueryModel = Depends(), session: Session = Depends(get_db)):
    rows, total = LawService.page(session, law_name=q.law_name,
                                   article_no=q.article_no)
    sliced = PageUtil.paginate(rows, q.page_num, q.page_size)
    return ResponseUtil.table(sliced, total)
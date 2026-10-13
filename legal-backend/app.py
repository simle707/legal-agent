import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from config.database import init_db
from config.env import AppConfig_
from exceptions.handler import register_exception_handlers
from module_law.controller.law_controller import law_controller
from module_law.controller.chat_controller import chat_controller
from module_law.controller.calculator_controller import calculator_controller
from core.rag_engine import set_engine, RAGEngine
from module_law.dao.law_dao import LawArticleDao
from config.database import get_session_local



@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：建表 + 加载法条构建 RAG 引擎
    init_db()
    db = get_session_local()()
    try:
        rows = LawArticleDao.list_all(db)
        articles = list(rows)
        try:
            from module_law.service.agent.llm_service import LLMService
            embed_fn = LLMService().embed
        except Exception:
            embed_fn = None
        set_engine(RAGEngine(articles, embed_fn=embed_fn))
        print(f'[startup] 法条加载 {len(articles)} 条')
    finally:
        db.close()
    yield

app = FastAPI(
    title=AppConfig_.app_name,
    description=AppConfig_.app_description,
    version=AppConfig_.app_version,
    lifespan=lifespan
)
register_exception_handlers(app)

app.include_router(law_controller, tags=["law"])
app.include_router(chat_controller, tags=["chat"])
app.include_router(calculator_controller, tags=["calculator"])

@app.get('/health', tags=["health"])
def health():
    from core.rag_engine import get_engine
    engine = get_engine()
    return {'status': 'ok', 'rag_mode': engine.mode if engine else None,
            'articles': len(engine.articles) if engine else 0}
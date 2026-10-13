# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends
import json
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from config.get_db import get_db
from utils.response_util import ResponseUtil
from module_law.entity.vo.chat_vo import ChatRequestModel, ChatResponseModel
from module_law.service.chat_service import ChatService

chat_controller = APIRouter(prefix='/chat', tags=['法律咨询对话'])


def _svc() -> ChatService:
    return ChatService()      # 单例，跨请求保留记忆


@chat_controller.post('/ask', summary='提问（Agent 工具调用）')
def ask(body: ChatRequestModel, session: Session = Depends(get_db)):
    def event_stream():
        for chunk in _svc().chat_stream(
            session_id=body.session_id,
            user_id=body.user_id,
            question=body.question,
            use_agent=body.use_agent,
            slots=body.slots
        ):
            print(chunk)
            yield f'data: {json.dumps(chunk, ensure_ascii=False)}\n\n'
        yield 'data: [DONE]\n\n'

    return StreamingResponse(
        event_stream(),
        media_type='text/event-stream',
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",    # 有 nginx 反代时禁用缓冲，否则照样整段吞
        }
    )

@chat_controller.post('/history', summary='查看会话历史')
def history(session_id: str, session: Session = Depends(get_db)):
    return ResponseUtil.success(data=ChatService().memory.get_history(session_id))


@chat_controller.delete('/history/{session_id}', summary='清空会话')
def clear(session_id: str, session: Session = Depends(get_db)):
    ChatService().memory.clear(session_id)
    return ResponseUtil.success(msg='已清空')

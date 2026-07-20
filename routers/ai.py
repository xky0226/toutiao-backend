from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx
from config.ai import ai_config

router = APIRouter(prefix="/api/ai", tags=["AI"])

# 请求体模型（定义前端发来的数据格式）
class ChatRequest(BaseModel):
    messages: list
    stream: bool


# 路由函数（接请求 → 拼 body → 调生成器 → 返回流
@router.post("/chat")
async def chat(request: ChatRequest):
    body = {"model": ai_config.model, "messages": request.messages, "stream": request.stream}
    headers = {"Authorization": f"Bearer {ai_config.api_key}", "Content-Type": "application/json"}

    # 异步生成器（边收DeepSeek的流，边转发）
    async def generate():
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream("POST", f"{ai_config.base_url}/chat/completions", json=body,
                                     headers=headers) as resp:
                async for chunk in resp.aiter_bytes():
                    yield chunk

    return StreamingResponse(generate(), media_type="text/event-stream")
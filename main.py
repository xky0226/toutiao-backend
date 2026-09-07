import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import news, users, favorite, history, ai
from scheduler import views_sync_loop
from utils.cache.client import close_redis



@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(views_sync_loop())
    yield  # ← 服务在这"活着"，处理请求
    # ⬇️ yield 之后 = 关闭时要做的事
    task.cancel()  # 给保安发"下班"信号
    try:
        await task  # 等他真停下来
    except asyncio.CancelledError:
        pass
    await close_redis()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  #允许的源,开发环境允许所有源,生产环境需要指定源
    allow_credentials=True,  # 允许携带cookie
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有请求头
)


#注册路由
app.include_router(news.router)

app.include_router(users.router)

app.include_router(favorite.router)

app.include_router(history.router)

app.include_router(ai.router)
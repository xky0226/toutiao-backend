import os

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession, create_async_engine

# 数据库URL
# ⚠️ 优先读环境变量 DATABASE_URL（部署 / 上 GitHub 用），本地没设时回落到本地开发串。
#    写死的那个 root:123456 只是本机开发密码，真部署时【必须】用环境变量覆盖。
ASYNC_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+aiomysql://root:123456@localhost:3306/news_app?charset=utf8mb4",
)


# 创建异步引擎
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=True, # 可选：输出SQL⽇志
    pool_size=10, # 设置连接池中保持的持久连接数
    max_overflow=20 # 设置连接池允许创建的额外连接数
)
# 创建异步会话⼯⼚
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)
# 依赖项，⽤于获取数据库会话
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
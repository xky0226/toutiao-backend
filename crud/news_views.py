from sqlalchemy import update
from config.db_conf import AsyncSessionLocal  # 开自己的 session（抄账不是请求上下文，不用 get_db 依赖）
from models.news import News
from utils.cache.client import get_redis
from utils.cache import keys

# Redis 6.2+ 才有 GETDEL；本机 3.0 不支持 → 用 Lua 模拟"原子取回并删除"（2.6+ 全兼容）
_GETDEL_LUA = """
local v = redis.call('GET', KEYS[1])
if v then
    redis.call('DEL', KEYS[1])
end
return v
"""


async def incr_views(news_id: int) -> int:
    """入账：浏览量 Redis INCR 原子 +1，同时把新闻 id 登记进 pending 名单。返回自增后的值。"""
    redis = await get_redis()
    count = await redis.incr(keys.news_views_key(news_id))
    await redis.sadd(keys.news_views_pending_key(), news_id)
    return count


async def sync_views_once() -> int:
    """执行一轮回写：把 pending 名单里所有未落库的增量写进 MySQL。返回成功回写条数。"""
    redis = await get_redis()
    members = await redis.smembers(keys.news_views_pending_key())
    if not members:
        return 0

    count = 0
    done = []
    async with AsyncSessionLocal() as session:
        try:
            for news_id in members:
                delta = await redis.eval(_GETDEL_LUA, 1, keys.news_views_key(news_id))
                if delta is None: # 僵尸：名单在但格子已空 → 划掉即可，无需落库
                    await redis.delete(keys.news_detail_key(int(news_id)))
                    await redis.srem(keys.news_views_pending_key(), news_id)
                    continue
                stmt = update(News).where(News.id == int(news_id)).values(
                    views=News.views + int(delta)
                )
                await session.execute(stmt)
                done.append(news_id)
                count += 1
            await session.commit()# 全部 execute 完，一次提交
            for news_id in done:
                await redis.delete(keys.news_detail_key(int(news_id)))
                await redis.srem(keys.news_views_pending_key(), news_id)# 落库成功才划名单（认账点）
        except Exception:
            await session.rollback()  # 失败：回滚，不划名单，留给下轮重试
            raise
    return count

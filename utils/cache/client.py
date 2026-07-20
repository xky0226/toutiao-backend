from redis import asyncio as aioredis
from config.redis import redis_config


_redis_pool = None

async def get_redis()-> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            redis_config.url,
            encoding="utf-8",
            decode_responses=redis_config.decode_responses,
        )

    return _redis_pool



async def close_redis():
    global _redis_pool
    if _redis_pool:
        await _redis_pool.close()
        _redis_pool = None




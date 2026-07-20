import json
import functools
from utils.cache.client import get_redis


def cached(ttl: int, key_builder: callable):


    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            redis = await get_redis()
            cache_key = key_builder(*args, **kwargs)

            #尝试从缓存获取
            cache_value = await redis.get(cache_key)
            if cache_value is not None:
                return json.loads(cache_value)


            #缓存未命中,重新运行原函数
            result = await func(*args, **kwargs)

            #原函数命中,写入缓存
            if result is not None:
                await redis.setex(cache_key, ttl, json.dumps(result, default=str))

            return result
        return wrapper
    return decorator








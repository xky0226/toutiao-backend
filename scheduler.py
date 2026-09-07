import asyncio
import logging
from crud.news_views import sync_views_once

logger = logging.getLogger(__name__)


async def views_sync_loop(interval: float = 60):
    """死循环：每 interval 秒抄一轮账。
    演示用 5 秒；生产建议 60 秒（抄太频繁 = 每轮大概率空跑白连 MySQL）。"""
    while True:
        try:
            await sync_views_once()
        except Exception:
            logger.exception("浏览量回写失败")  # ← 关键：吞掉，不能让它死
        await asyncio.sleep(interval)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import joinedload
from models.history import History
from models.news import News

async def add_history(db: AsyncSession, user_id: int, news_id: int) -> History:
    history = History(user_id=user_id, news_id=news_id)

    db.add(history)
    await db.flush()
    await db.refresh(history)
    return history

async def get_history_list(db, user_id, skip, page_size):
    stmt = (select(History)
            .options(joinedload(History.news)). #JOIN news 表获取新闻信息
            where(History.user_id == user_id).
            order_by(History.view_time.desc()).
            offset(skip).
            limit(page_size))

    result = await db.execute(stmt)
    histories = result.scalars().all()

    count_stmt = select(func.count(History.id)).where(History.user_id == user_id)
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    items = []
    for history in histories:
        items.append({
            'id': history.news.id,
            'title': history.news.title,
            "description": history.news.description,
            "image": history.news.image,
            "author": history.news.author,
            "publishTime": history.news.publish_time,
            "categoryId": history.news.category_id,
            "views": history.news.views,
            "viewTime": history.view_time
        })

    return items, total

async def clear_history(db, user_id):
    stmt = delete(History).where(History.user_id == user_id)
    result = await db.execute(stmt)
    await db.flush()
    return result.rowcount

async def remove_history(db, history_id, user_id) -> bool:
    stmt = select(History).where(History.id == history_id, History.user_id == user_id)
    result = await db.execute(stmt)

    if not result.scalar():
        return False

    delete_his = delete(History).where(History.id == history_id, History.user_id == user_id)
    result = await db.execute(delete_his)
    await db.flush()
    return True


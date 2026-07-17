from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import joinedload
from models.favorite import Favorite
from models.news import News

# 查 favorite 表
async def check_favorite(db, user_id, news_id) -> bool:
    stmt = select(Favorite).where(Favorite.user_id == user_id,
                                  Favorite.news_id == news_id)
    result = await db.execute(stmt)
    favorite = result.scalar_one_or_none()
    if not favorite:
        return False
    else:
        return True

#添加收藏
async def add_favorite(db, user_id, news_id) -> Favorite:
    favorite = Favorite(user_id=user_id, news_id=news_id)

    db.add(favorite)
    await db.flush()
    await db.refresh(favorite)
    return favorite

#删除收藏新闻
async def remove_favorite(db, user_id, news_id) -> bool:
    stmt = select(Favorite).where(Favorite.user_id == user_id,
                                  Favorite.news_id == news_id)
    result = await db.execute(stmt)
    favorite = result.scalar_one_or_none()
    if not favorite:
        return False

    db.delete(favorite)
    await db.flush()  #refresh是重新读取,删掉了不能重新读取,否则会报错
    return True

#一次性删除所有收藏
async def clear_favorites(db, user_id) -> int:
    stmt = delete(Favorite).where(Favorite.user_id == user_id)
    result = await db.execute(stmt)
    await db.flush()
    return result.rowcount


 # 分页查询该用户的收藏列表
async def get_favorite_list(db, user_id, skip, page_size):
    stmt = (select(Favorite).
            options(joinedload(Favorite.news)). #JOIN news 表获取新闻信息
            offset(skip).
            limit(page_size).
            where(Favorite.user_id == user_id,))

    result = await db.execute(stmt)
    favorites = result.scalars().all()

    #查询总数
    count_stmt = select(func.count(Favorite.id)).where(Favorite.user_id == user_id)
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    #组装数据
    item=[]
    for fav in favorites:
        item.append({
            "id" : fav.news.id,
            "title": fav.news.title,
            "description": fav.news.description,
              "image": fav.news.image,
              "author": fav.news.author,
              "publishTime": fav.news.publish_time,
              "categoryId": fav.news.category_id,
              "views": fav.news.views,
              "favoriteTime": fav.created_at
        })

    return item,total

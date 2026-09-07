from fastapi import APIRouter,Depends,HTTPException
from fastapi.params import Query
from sqlalchemy.ext.asyncio import AsyncSession
from utils.cache.decorator import cached
from utils.cache import keys
from config.db_conf import get_db
from crud import news, news_views


#创建APIrouter实例
router = APIRouter(prefix="/api/news", tags=["news"])

#新闻分类

@cached(ttl=3600, key_builder=lambda *a,**kw:keys.categories_key())
async def get_categories_cached(db):
    categories = await news.get_categories(db, skip=0, limit=100)
    # ORM对象 → 纯字典，JSON才能序列化
    return [
        {"id": c.id, "name": c.name, "sort_order": c.sort_order}
        for c in categories
    ]

@router.get("/categories")
async def get_categories(db: AsyncSession = Depends(get_db)):
    #先获取数据库里的新闻分类数据————》定义模型类————〉封装查询数据的方法
    categories = await get_categories_cached(db)
    return {
        "code" :200,
        "message": "获取新闻分类成功",
        "data" : categories
    }


#新闻列表


@cached(ttl=300, key_builder=lambda cat_id, page, page_size, db:
        keys.news_list_key(cat_id, page, page_size))
async def get_news_list_cached(
        category_id: int,
        page: int,
        page_size: int,
        db: AsyncSession):
    offset = (page - 1) * page_size
    news_list = await news.get_news_list(db, category_id, offset, page_size)
    total = await news.get_news_count(db, category_id)
    has_more = (offset + len(news_list)) < total
    return {
        "list": [
            {
                "id": n.id,
                "title": n.title,
                "description": n.description,
                "image": n.image,
                "author": n.author,
                "categoryId": n.category_id,
                "views": n.views,
                "publishTime": str(n.publish_time) if n.publish_time else None
            }
            for n in news_list
        ],
        "total": total,
        "hasMore": has_more
    }


@router.get("/list")
async def get_news(
        category_id :int = Query(..., alias ="categoryId"),
        page :int = 1,
        page_size :int = Query(10,le=100,alias ="pageSize"),
        db: AsyncSession = Depends(get_db)
):
    data = await get_news_list_cached(category_id, page, page_size, db)
    return {
        "code" :200,
        "message": "获取新闻列表成功",
        "data" : data
    }




@cached(ttl=600, key_builder=lambda news_id,*a,**kw: keys.news_detail_key(news_id))
async def get_news_detail_cached(news_id :int,db):
    news_detail = await news.get_news_detail(db,news_id)
    if not news_detail:
        return None
    return {
            "id": news_detail.id,
            "title": news_detail.title,
            "content": news_detail.content,
            "image": news_detail.image,
            "author": news_detail.author,
            "publishTime": news_detail.publish_time,
            "categoryId": news_detail.category_id,
            "views": news_detail.views
    }




@cached(ttl=600, key_builder=lambda news_id,*a,**kw: keys.news_detail_key(news_id) + ":related")
async def get_related_news_cached(news_id: int, category_id: int, db):
    # crud 已经返回了字典列表，直接返回即可
    return await news.get_related_news(db, news_id, category_id)


@router.get("/detail")
async def get_news_detail(news_id :int = Query(..., alias ="id"),db: AsyncSession = Depends(get_db)):
    #获取新闻详情 + 浏览量+1 + 相关新闻
    news_detail = await get_news_detail_cached(news_id, db)
    if not news_detail:
        raise HTTPException(status_code=404, detail="新闻不存在")

    views_res= await news_views.incr_views(news_id)
    if not views_res:
        raise HTTPException(status_code=500, detail="新闻不存在")

    related_news = await get_related_news_cached(news_detail["id"] ,news_detail["categoryId"], db)

    news_detail["views"] = news_detail["views"] + views_res
    news_detail["relatedNews"] = related_news

    return {
        "code" :200,
        "message": "获取新闻详情成功",
        "data" :news_detail
    }



from fastapi import APIRouter, Depends, HTTPException
from fastapi.params import Query
from sqlalchemy.ext.asyncio import AsyncSession
from config.db_conf import get_db
from routers.users import get_current_user
from models.users import User
from models.news import News
from crud import favorite
from schemas.favorite import FavoriteRequest




router = APIRouter(prefix="/api/favorite", tags=["favorite"])



@router.get("/check")
async def check( news_id: int = Query(..., alias="newsId"),
                 db: AsyncSession = Depends(get_db),
                 current_user:User = Depends(get_current_user)):
    user_id = current_user.id
    is_fav = await favorite.check_favorite(db, user_id, news_id)

    return {
        "code": 200,
        "message": "success",
        "data": {
            "isFavorite": is_fav,
        }
    }


@router.post("/add")
async def add_favorite(req: FavoriteRequest,
                       db: AsyncSession = Depends(get_db),
                       current_user:User = Depends(get_current_user)):
    user_id: int = current_user.id
    add_data = await favorite.add_favorite(db, user_id, req.newsId)
    return {
        "code": 200,
        "message": "收藏成功",
        "data": {
            "id": add_data.id,
            "userId": add_data.user_id,
            "newsId": add_data.news_id,
            "createTime": add_data.created_at
        }
    }



@router.delete("/remove")
async def remove_favorite(news_id: int = Query(..., alias="newsId"),
                          db: AsyncSession = Depends(get_db),
                          current_user:User = Depends(get_current_user)):
    user_id: int = current_user.id
    remove_data = await favorite.remove_favorite(db, user_id, news_id)
    if not remove_data:
        raise HTTPException(status_code=404, detail="该收藏不存在")


    return {
        "code": 200,
        "message": "取消收藏成功",
        "data": None
    }


@router.get("/list")
async def list_favorite(page: int = Query(1, alias="page", ge=1),
                        page_size: int = Query(10, alias="pageSize", ge=1, le=50),
                        db: AsyncSession = Depends(get_db),
                        current_user:User = Depends(get_current_user)):
    user_id = current_user.id
    skip = (page - 1) * page_size
    item, total = await favorite.get_favorite_list(db, user_id, skip, page_size)


    return {
        "code": 200,
        "message": "success",
        "data": {
            "list": item,
            "total": total,
            "hasMore": (skip + page_size) < total
        }
    }

@router.delete("/clear")
async def clear_favorite(db: AsyncSession = Depends(get_db),
                         current_user:User = Depends(get_current_user)):
    clear_count = await favorite.clear_favorites(db, current_user.id)
    return {
        "code": 200,
        "message": f"成功删除{clear_count}条收藏记录",
        "data": None
    }



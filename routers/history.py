from fastapi import APIRouter, Depends, HTTPException
from fastapi.params import Query
from sqlalchemy.ext.asyncio import AsyncSession
from config.db_conf import get_db
from routers.users import get_current_user
from models.users import User
from models.history import History
from crud import history
from schemas.history import HistoryRequest

router = APIRouter(prefix="/api/history", tags=["history"])


@router.post("/add")
async def add_history(req: HistoryRequest,
                      db: AsyncSession = Depends(get_db),
                      current_user: User = Depends(get_current_user)):

    add_data = await history.add_history(db, current_user.id, req.newsId)

    return {
        "code": 200,
        "message": "添加成功",
        "data": {
            "id": add_data.id,
            "userId": add_data.user_id,
            "newsId": add_data.news_id,
            "viewTime": add_data.view_time
        }
    }


@router.get("/list")
async def list_history(page: int = Query(1, alias="page", ge=1),
                       page_size: int = Query(10, alias="pageSize", ge=1, le=50),
                       db: AsyncSession = Depends(get_db),
                       current_user: User = Depends(get_current_user)
                       ):
    user_id = current_user.id
    skip = (page - 1) * page_size
    item,total = await history.get_history_list(db, user_id, skip, page_size)
    return {
        "code": 200,
        "message": "success",
        "data": {
            "list": item,
            "total": total,
            "hasMore": (skip + page_size) < total
        }
    }





@router.delete("/delete/{history_id}")
async def delete_history(history_id: int,
                         db: AsyncSession = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    user_id = current_user.id
    deleted = await history.remove_history(db, history_id, user_id)

    return {
        "code": 200,
        "message": "删除成功",
        "data": None
    }


@router.delete("/clear")
async def clear_history(db: AsyncSession = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    user_id = current_user.id
    cleared = await history.clear_history(db, user_id)
    return {
        "code": 200,
        "message": "清空成功",
        "data": None
    }

from pydantic import BaseModel
from typing import Optional, List

#添加收藏的请求
class FavoriteRequest(BaseModel):
    newsId: int

#收藏状态的响应 — 给 check 接口用
class FavoriteCheckResponse(BaseModel):
    isFavorite: bool


#收藏列表中的单条新闻数据 — 给 list 接口用
class FavoriteNewsResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    image: Optional[str] = None
    author: Optional[str] = None
    publishTime: Optional[str] = None
    categoryId: int
    views: int = 0
    favoriteTime: str

#收藏列表的完整响应 — 给 list 接口用
class FavoriteListResponse(BaseModel):
    list: List[FavoriteNewsResponse] = []
    total: int = 0
    hasMore: bool = False
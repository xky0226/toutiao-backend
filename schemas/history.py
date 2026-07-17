from pydantic import BaseModel
from typing import Optional, List

#list接口用
class HistoryNewsResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    image: Optional[str] = None
    author: Optional[str] = None
    publishTime: Optional[str] = None  # publish_time
    categoryId: int
    views: int = 0
    viewTime: str  # history.view_time，最近浏览时间


# 浏览记录列表响应
class HistoryListResponse(BaseModel):
    list: List[HistoryNewsResponse] = []
    total: int = 0
    hasMore: bool = False


class HistoryRequest(BaseModel):
    newsId: int
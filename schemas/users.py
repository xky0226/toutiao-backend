from pydantic import BaseModel
from typing import Optional, Generic, TypeVar

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    code: int = 200
    message: str = "success"
    data: T


#注册/登录请求 — 共用一个
class UserRequest(BaseModel): 
    username: str
    password: str

#用户信息响应模型 — 返回给前端的用户数据结构
class UserInfoResponse(BaseModel):
    id: int
    username: str
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    gender: Optional[str] = None
    bio: Optional[str] = None

# 注册/登录的完整响应 — 包含 token + userInfo
class UserLoginResponse(BaseModel):
    token: str
    userInfo: UserInfoResponse

#更新用户信息请求 — 所有字段都可选
class UserUpdateRequest(BaseModel):
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    gender: Optional[str] = None
    bio: Optional[str] = None
    phone: Optional[str] = None

#修改密码
class UserPasswordRequest(BaseModel):
    oldPassword: str
    newPassword: str




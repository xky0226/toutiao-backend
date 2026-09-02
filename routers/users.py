from fastapi import APIRouter,Depends,HTTPException,Header
from utils import response
from config.db_conf import get_db
from fastapi.params import Query
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.users import UserRequest,UserUpdateRequest,UserPasswordRequest,UserInfoResponse,UserLoginResponse, ApiResponse
from models.users import User
from crud import users,favorite,history



router = APIRouter(prefix="/api/user", tags=["users"])


@router.post("/register")
async def register(user_data :UserRequest,db :AsyncSession = Depends(get_db)):
    user = await users.create_user(db, user_data.username, user_data.password)
    user_token = await users.create_token(db, user.id)

    return {
        "code" :200,
        "message": "注册成功",
        "data" : {
            "token" : user_token.token,
            "userInfo" : {
                "id" : user.id,
                "username" : user_data.username,
                "bio" : user.bio,
                "avatar" : user.avatar
            }
        }
    }

#token校验
async def get_current_user(authorization: str = Header(None),
      db: AsyncSession = Depends(get_db)
  ) -> User:
    if not authorization:
        raise HTTPException(status_code=401, detail="未提供认证令牌")
    user = await users.get_user_by_token(db, authorization)
    if not user:
        raise HTTPException(status_code=401, detail="令牌无效或已过期")
    return user


@router.post("/login")
async def login(user_data :UserRequest,db :AsyncSession = Depends(get_db)):

    user = await users.authenticate_user(db, user_data.username, user_data.password)
    if not user:
        raise HTTPException(status_code=401,detail="用户名或密码错误")
    user_token = await users.create_token(db, user.id)

    return {
        "code" : 200,
        "message" : "登陆成功",
        "data" : {
            "token" : user_token.token,
            "userInfo" : {
                "id" : user.id,
                "username" : user.username,
                "nickname": user.nickname,
                "avatar": user.avatar,
                "bio": user.bio,
            }
        }
    }


#通过id进行查找用户信息
@router.get("/info",response_model=ApiResponse[UserInfoResponse])
async def info(current_user: User = Depends(get_current_user)):
    data = {
        "id": current_user.id,
        "username": current_user.username,
        "nickname": current_user.nickname,
        "avatar": current_user.avatar,
        "gender": current_user.gender,
        "bio": current_user.bio
    }
    return response.ok(data, "查询成功")


#更新用户数据
@router.put("/update")
async def user_update(user_data :UserUpdateRequest,
                      db :AsyncSession = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    user = await users.update_user(db, current_user.id,
                             user_data.nickname,
                             user_data.avatar,
                             user_data.gender,
                             user_data.bio,
                             user_data.phone)

    return {
        "code": 200,
        "message": "更新成功",
        "data": {
            "id": user.id,
            "username": current_user.username,
            "nickname": user.nickname,
            "avatar": user.avatar,
            "gender": user.gender,
            "bio": user.bio
        }
    }

@router.put("/password")
async def user_password(user_data:UserPasswordRequest,
                        db:AsyncSession = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    user = await users.update_password(db, current_user.id,user_data.oldPassword, user_data.newPassword)

    return {
        "code": 200,
        "message": "密码修改成功",
        "data": None
    }


@router.delete("/account")
async def account_delete(db:AsyncSession = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    favorite_delete = await favorite.clear_favorites(db, current_user.id)
    history_delete = await history.clear_history(db, current_user.id)
    user_delete = await users.clear_user(db, current_user.id)
    if user_delete == 0:
        raise HTTPException(status_code=404, detail="没有发现该用户,请确认用户id是否正确")

    return {"code": 200,
            "message": "注销成功",
            "data": {
                "favorites" : favorite_delete,
                "history" : history_delete
                }
            }


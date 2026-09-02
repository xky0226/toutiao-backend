from datetime import datetime, timedelta
from typing import Optional
import secrets
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from passlib.context import CryptContext
from models.users import User, UserToken

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

#创建用户
async def  create_user(db: AsyncSession, username: str, password: str):
    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名已存在")

    # # 密码加密 + 创建
    hashed_password = pwd_context.hash(password)
    new_user = User(username=username, password=hashed_password)
    db.add(new_user)

    #只需 refresh 获取自增 id，不需要 commit(自动commit)
    await db.flush()
    await db.refresh(new_user)

    return new_user

#登录,对比账号和密码
async def authenticate_user(db: AsyncSession, username: str, password: str):
    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:#没拿到任何数据,证明账号不存在
        return None
    if not pwd_context.verify(password, user.password):#对比密码是否正确
        return None
    return user

#通过id查询用户
async def get_user_by_id(db: AsyncSession, user_id)-> Optional[User]:
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    return user

#更新个人数据
async def update_user(db: AsyncSession, user_id:int,
                      nickname: Optional[str] = None,
                      avatar: Optional[str] = None,
                      gender: Optional[str] = None,
                      bio: Optional[str] = None,
                      phone: Optional[str] = None) ->Optional[User]:
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        return None
    if nickname is not None:
        user.nickname = nickname
    if avatar is not None:
        user.avatar = avatar
    if gender is not None:
        user.gender = gender
    if bio is not None:
        user.bio = bio
    if phone is not None:
        user.phone = phone

    await db.flush()
    await db.refresh(user)
    return user


#修改密码
async def update_password(db: AsyncSession,
                          user_id: int,
                          old_password: str,
                          new_password: str) -> bool:
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        return False

    if not pwd_context.verify(old_password, user.password) :
        return False

    user.password = pwd_context.hash(new_password)
    await db.flush()
    return True


#创建登陆令牌
async def create_token(db: AsyncSession, user_id: int) -> UserToken:
    #随机生成字符串
    token_str= secrets.token_urlsafe(32)
    #创建时间
    expires_at = datetime.utcnow() + timedelta(days=7)
    user_token = UserToken(user_id=user_id, token=token_str, expires_at=expires_at)
    db.add(user_token)
    await db.flush()
    await db.refresh(user_token)
    return user_token


async def get_user_by_token(db: AsyncSession, token: str) -> Optional[User]:
    stmt = select(UserToken).where(UserToken.token == token)
    result = await db.execute(stmt)
    user_token = result.scalar_one_or_none()

    if not user_token:
        return None

    #如果令牌过期
    time = user_token.expires_at
    if time < datetime.utcnow():
        return None

    #查找并返回用户信息
    stmt = select(User).where(User.id == user_token.user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

#删除用户
async def clear_user(db: AsyncSession, user_id: int) -> int:
    stmt = delete(User).where(User.id == user_id)
    result = await db.execute(stmt)
    await db.flush()
    return result.rowcount



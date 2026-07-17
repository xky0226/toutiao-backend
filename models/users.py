from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, Text, ForeignKey, DateTime
from models.news import Base

class User(Base):
    __tablename__ = "user"


    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="用户ID")
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="用户名")
    password: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码")
    nickname: Mapped[Optional[str]] = mapped_column(String(50), comment="昵称")
    avatar: Mapped[Optional[str]] = mapped_column(String(255), comment="头像URL")
    gender: Mapped[Optional[str]] = mapped_column(String(10), default="unknown", comment="性别")
    bio: Mapped[Optional[str]] = mapped_column(Text, comment="个人简介")
    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True, comment="手机号")


class UserToken(Base):
    __tablename__ = "user_token"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="令牌id")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False, comment="用户id")
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, comment="令牌值")
    expires_at: Mapped[datetime] = mapped_column( DateTime, nullable=False, comment="过期时间")
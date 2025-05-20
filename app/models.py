from typing import Optional, List, Any
import uuid
from datetime import datetime
from typing import Literal
from loguru import logger

from pydantic import EmailStr, BaseModel, validator, field_validator, model_validator
from sqlalchemy import UniqueConstraint, Column, String, Integer, Text, DateTime, Boolean, ARRAY, func
from sqlmodel import Field, Relationship, SQLModel, select
from sqlalchemy.dialects.postgresql import JSONB
from app.utils import process_image_urls


# 这个算是用户表的基类，其他的用户表继承这个基类
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)
    cookies: Optional[int] = None  # 设置为可选字段


# Properties to receive via API on creation
# 定义用户创建时 API 端点期望接收的请求体的数据结构和验证规则。
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=40)

#名为UserRegister的模型，用于注册用户
#定义用户注册时 API 端点
#（具体来说是 POST /api/v1/users/signup）期望接收的请求体的数据结构和验证规则。
class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=40)
    full_name: str | None = Field(default=None, max_length=255)
    verify_code: str = Field(min_length=6, max_length=6)

# 更新用户信息，这里继承了UserBase，然后添加了email和password
class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=40)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=40)
    new_password: str = Field(min_length=8, max_length=40)


# 数据库模型，数据库表从类名推断，会去访问user表 通过继承UserBase，然后添加uuid,哈希加密的密码
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    items: list["Item"] = Relationship(back_populates="owner", cascade_delete=True)
    cookies: Optional[int] = 3  # 设置为可选字段


# 返回给前端的用户信息，这里继承了UserBase，然后添加了uuid标识符
class UserPublic(UserBase):
    id: uuid.UUID


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Shared properties
class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Properties to receive on item creation
class ItemCreate(ItemBase):
    pass


# Properties to receive on item update
class ItemUpdate(ItemBase):
    title: str | None = Field(default=None, min_length=1, max_length=255)  # type: ignore


# Database model, database table inferred from class name
class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="items")


# Properties to return via API, id is always required
class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=40)


# 请求回复卡片的图片
class ImagePathInfo(BaseModel):
    original_filename: Optional[str] = None # 原图片名称
    relativePath: str # 图片url，图床分配的


#聊天内容的卡片
class DefaultCardBase(SQLModel):
    id: Optional[str] = Field(default=None)
    content: Optional[str] = Field(default=None)
    time: Optional[str] = Field(default=None)
    category: Optional[str] = Field(default=None)
    thumbs: Optional[int] = Field(default=0)

class DefaultCard(DefaultCardBase, table=True):
    __tablename__ = "defaultcard" # type: ignore
    number: int = Field(default=None, primary_key=True, index=True)
    imageUrls: Optional[List[str]] = Field(default=None, sa_column=Column(ARRAY(String)))
    

#响应的卡片
class DefaultCardResponse(SQLModel):
    data: list[DefaultCard]

    @model_validator(mode='after')
    def process_image_urls_in_response(self) -> 'DefaultCardResponse':
        if self.data:
            for card_instance in self.data:
                process_image_urls(card_instance)
        return self

#请求话题的卡片
class CardRequest(BaseModel):
    skip: int = 0
    category: str
#请求最新的一个卡片
class CardRequest_New(BaseModel):
    category: str

#请求回复卡片的内容
class ReplyCardRequest(BaseModel):
    number: int
    skip: int = 0

#添加的卡片，客户端发送的卡片
class AddCard(BaseModel):
    id: str
    content: str
    time: str
    category: str
    imageUrls: Optional[List[ImagePathInfo]] = Field(default=None)

#注册时候发送的验证码
class VerifyCodeRequest(BaseModel):
    email: str


#添加的回复卡片，客户端发送
class AddReplyCard_Client(BaseModel):
    number: int
    id: str
    content: str
    time: str
    reply: str|None=None #回复内容,可以为空
    imageUrls: Optional[List[ImagePathInfo]] = Field(default=None)

#添加回复卡片,数据库存储
class AddReplyCard(SQLModel,table=True):
    number_primary: uuid.UUID = Field(primary_key=True,default_factory=uuid.uuid4)#主键,默认生成一个uuid
    number: int = Field(foreign_key="defaultcard.number", nullable=False)
    #通过外键和DefaultCard关联
    id: str
    content: str
    time: str
    reply: str|None=None #回复内容,可以为空
    thumbs: int
    imageUrls: Optional[List[str]] = Field(default=None, sa_column=Column(ARRAY(String)))

#添加回复卡片的响应
class AddReplyCardResponse(SQLModel):
    data: list[AddReplyCard]

    @model_validator(mode='after')
    def process_reply_card_image_urls_in_response(self) -> 'AddReplyCardResponse':
        if self.data:
            for card_instance in self.data:
                process_image_urls(card_instance)
        return self

class Cookie(SQLModel,table=True):
    name: str = Field(primary_key=True)
    time: str
    isbanned: bool
    inused: bool
    id: uuid.UUID = Field(foreign_key="user.id",nullable=False)#外键,关联用户表

class CookieResponse(SQLModel):
    data: list[Cookie]

#cookie的启用
class CookieUse(SQLModel):
    name: str

#获取用户cookie数量
class GetUserCookieNum(SQLModel):
    number: int
class ReplyLike(SQLModel, table=True):
    reply_id: str=Field(primary_key=True)
    user_id: uuid.UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)
    __table_args__ = (
        # 防止重复点赞
        UniqueConstraint("reply_id", "user_id"),
    )

class LikeRequest(BaseModel):
    reply_id: str
    action: Literal["like", "unlike"]

# 上传图片的数据结构

class ImageDataLinks(BaseModel):
    url: str #图片访问的url
    html: str
    bbcode: str
    markdown: str
    markdown_with_link: str
    thumbnail_url: str #缩略图

class ImageData(BaseModel):
    key: str
    name: str
    pathname: str
    origin_name: str
    size: float
    mimetype: str
    extension: str
    md5: str
    sha1: str
    links: ImageDataLinks

class ImageUploadResponse(BaseModel):
    status: bool
    message: str
    data: Optional[ImageData] = None #图片数据,可以为空

# 客户端请求过来的数据
class ImageUploadRequest(BaseModel):
    pass # Add pass to make it a valid empty class definition

#重设密码
class UserResetPassword(SQLModel):
    email: EmailStr = Field(
        max_length=255,
        description="用户邮箱地址",
    )
    verify_code: str = Field(
        min_length=6,
        max_length=6,
        description="6位验证码",
    )
    password: str = Field(
        min_length=8,
        max_length=40,
        description="新密码，长度8-40个字符",
    )

# 用户寻找自己发布的话题的卡片请求
class UserFindCardRequest(BaseModel):
    Cookie:str #cookie ID
    skip:int=0

# 用户寻找自己发布的回复卡片的响应
class UserFindCardResponse(SQLModel):
    DefaultCard: List[DefaultCard]
    AddReplyCard: List[AddReplyCard]

    @model_validator(mode='after')
    def process_reply_card_image_urls_in_response(self) -> 'UserFindCardResponse':
        # 处理 AddReplyCard
        if self.AddReplyCard:
            for card_instance in self.AddReplyCard:
                process_image_urls(card_instance)
        # 处理 DefaultCard
        if self.DefaultCard:
            for card_instance in self.DefaultCard:
                process_image_urls(card_instance)
        return self

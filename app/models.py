from typing import Optional, List, Any
import uuid
from datetime import datetime
from typing import Literal
from loguru import logger

from pydantic import EmailStr, BaseModel, validator, field_validator, model_validator
from sqlalchemy import UniqueConstraint, Column, String, Integer, Text, DateTime, Boolean, ARRAY, func
from sqlmodel import Field, Relationship, SQLModel, select
from sqlalchemy.dialects.postgresql import JSONB


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
        # from loguru import logger # If logging can be made to work, it would be useful here
        # logger.debug("DefaultCardResponse validator: Processing imageUrls for response.")
        if self.data:
            for card_instance in self.data:
                # Check if imageUrls exists, is a list, is not empty, and looks like a char-split array
                if hasattr(card_instance, 'imageUrls') and \
                   card_instance.imageUrls is not None and \
                   isinstance(card_instance.imageUrls, list) and \
                   len(card_instance.imageUrls) > 0:
                    
                    first_val = card_instance.imageUrls[0]
                    # Ensure there's a last element to check for symmetrical braces
                    if len(card_instance.imageUrls) > 1:
                        last_val = card_instance.imageUrls[-1]
                    else: # Only one element, can't be a matched pair of braces
                        last_val = None 

                    # Condition to identify the char-split string: list of strings, starts with '{', ends with '}'
                    if isinstance(first_val, str) and first_val == '{' and \
                       isinstance(last_val, str) and last_val == '}':
                        
                        # logger.debug(f"DefaultCardResponse: Card {getattr(card_instance, 'number', 'N/A')}: imageUrls appears char-split. Rejoining.")
                        rejoined_string = "".join(str(char_or_item) for char_or_item in card_instance.imageUrls)
                        # logger.debug(f"DefaultCardResponse: Card {getattr(card_instance, 'number', 'N/A')}: Rejoined to: {rejoined_string}")
                        
                        # Now parse the rejoined string (which should be like "{path1,path2}")
                        if rejoined_string.startswith("{") and rejoined_string.endswith("}"):
                            stripped_value = rejoined_string[1:-1]
                            if not stripped_value: # Handles empty array string "{}"
                                card_instance.imageUrls = []
                            else:
                                card_instance.imageUrls = [item.strip() for item in stripped_value.split(',') if item.strip()]
                            # logger.debug(f"DefaultCardResponse: Card {getattr(card_instance, 'number', 'N/A')}: Parsed to: {card_instance.imageUrls}")
                        # else: logger.warning(f"DefaultCardResponse: Card {getattr(card_instance, 'number', 'N/A')}: Rejoined string doesn't have expected format: {rejoined_string}")
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
        # from loguru import logger # Optional: uncomment if logger is configured and needed for debugging
        # logger.debug("AddReplyCardResponse validator: Processing imageUrls for response.")
        if self.data:
            for card_instance in self.data:
                if hasattr(card_instance, 'imageUrls') and \
                   card_instance.imageUrls is not None and \
                   isinstance(card_instance.imageUrls, list) and \
                   len(card_instance.imageUrls) > 0:
                    
                    first_val = card_instance.imageUrls[0]
                    if len(card_instance.imageUrls) > 1:
                        last_val = card_instance.imageUrls[-1]
                    else:
                        last_val = None

                    if isinstance(first_val, str) and first_val == '{' and \
                       isinstance(last_val, str) and last_val == '}':
                        
                        # logger.debug(f"AddReplyCardResponse: Card ID {getattr(card_instance, 'id', 'N/A')}: imageUrls appears char-split. Rejoining.")
                        rejoined_string = "".join(str(char_or_item) for char_or_item in card_instance.imageUrls)
                        # logger.debug(f"AddReplyCardResponse: Card ID {getattr(card_instance, 'id', 'N/A')}: Rejoined to: {rejoined_string}")
                        
                        if rejoined_string.startswith("{") and rejoined_string.endswith("}"):
                            stripped_value = rejoined_string[1:-1]
                            if not stripped_value:
                                card_instance.imageUrls = []
                            else:
                                card_instance.imageUrls = [item.strip() for item in stripped_value.split(',') if item.strip()]
                            # logger.debug(f"AddReplyCardResponse: Card ID {getattr(card_instance, 'id', 'N/A')}: Parsed to: {card_instance.imageUrls}")
                        # else: logger.warning(f"AddReplyCardResponse: Card ID {getattr(card_instance, 'id', 'N/A')}: Rejoined string not in expected format: {rejoined_string}")
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
class CardFavorite(SQLModel, table=True):
    card_number=int=Field(primary_key=True)
    user_id: uuid.UUID
    __table_args__ = (
        # 防止重复点赞
        UniqueConstraint("card_number", "user_id"),
    )
class FavoriteRequest(BaseModel):
    card_number: int
    action: Literal["favorite", "unfavorite"]
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





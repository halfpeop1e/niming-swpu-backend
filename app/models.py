import uuid

from pydantic import EmailStr, BaseModel
from sqlmodel import Field, Relationship, SQLModel


# 这个算是用户表的基类，其他的用户表继承这个基类
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


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

#聊天内容的卡片
class DefaultCard(SQLModel,table=True):
    number: int = Field(primary_key=True)#主键,可以自增
    id: str
    content: str
    time: str

#响应的卡片
class DefaultCardResponse(SQLModel):
    data: list[DefaultCard]

#请求话题的卡片
class CardRequest(BaseModel):
    skip: int = 0

#请求回复卡片的内容
class ReplyCardRequest(BaseModel):
    number: int
    skip: int = 0

#添加的卡片，客户端发送的卡片
class AddCard(BaseModel):
    id: str
    content: str
    time: str

#添加的回复卡片，客户端发送
class AddReplyCard_Client(BaseModel):
    number: int
    id: str
    content: str
    time: str
    reply: str|None=None #回复内容,可以为空
    time: str

#添加回复卡片,数据库存储
class AddReplyCard(SQLModel,table=True):
    number_primary: uuid.UUID = Field(primary_key=True,default_factory=uuid.uuid4)#主键,默认生成一个uuid
    number: int = Field(foreign_key="defaultcard.number", nullable=False)
    #通过外键和DefaultCard关联
    id: str
    content: str
    time: str
    reply: str|None=None #回复内容,可以为空
    time: str
    thumbs: int

#添加回复卡片的响应
class AddReplyCardResponse(SQLModel):
    data: list[AddReplyCard]



import uuid
from typing import Any

from sqlmodel import Session, select

from app.core.security import get_password_hash, verify_password
from app.models import Item, ItemCreate, User, UserCreate, UserUpdate, DefaultCard, AddReplyCard, Cookie

#向数据库中添加新卡片的函数实现
async def create_card(*, session: Session, card_in: DefaultCard) -> DefaultCard:
    """
    Adds a new card record to the database.
    Assumes card_in is a pre-validated DefaultCard instance.
    """
    db_card = card_in
    session.add(db_card)
    await session.commit()
    await session.refresh(db_card)
    return db_card

#向数据库中添加新回复卡片的函数实现
async def create_reply_card(*, session: Session, reply_card_in: AddReplyCard) -> AddReplyCard:
    """
    这个函数是向数据库中添加新回复卡片的函数实现
    """
    db_reply_card = reply_card_in
    session.add(db_reply_card)
    await session.commit()
    await session.refresh(db_reply_card)
    return db_reply_card


#向数据库中添加新用户的函数实现
async def create_user(*, session: Session, user_create: UserCreate) -> User:
    db_obj = User.model_validate(
        user_create, update={"hashed_password": get_password_hash(user_create.password)}
    )
    session.add(db_obj)
    await session.commit()
    await session.refresh(db_obj)
    return db_obj

#这个函数会获取用户输入的明文密码 (password)
#和从数据库中读取的该用户的哈希密码 (db_user.hashed_password)
async def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> Any:
    user_data = user_in.model_dump(exclude_unset=True)
    extra_data = {}
    if "password" in user_data:
        password = user_data["password"]
        hashed_password = get_password_hash(password)
        extra_data["hashed_password"] = hashed_password
    db_user.sqlmodel_update(user_data, update=extra_data)
    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)
    return db_user

#更新用户的cookies
async def update_user_cookies(*, session: Session, db_user: User, cookies: int) -> Any:
    db_user.cookies = cookies
    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)
    return db_user

async def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    result = await session.exec(statement)
    session_user = result.first()
    return session_user


async def authenticate(*, session: Session, email: str, password: str) -> User | None:
    db_user = await get_user_by_email(session=session, email=email)
    if not db_user:
        return None
    if not verify_password(password, db_user.hashed_password):
        return None
    return db_user


async def create_item(*, session: Session, item_in: ItemCreate, owner_id: uuid.UUID) -> Item:
    db_item = Item.model_validate(item_in, update={"owner_id": owner_id})
    session.add(db_item)
    await session.commit()
    await session.refresh(db_item)
    return db_item

async def get_user_for_cookie_operation(session: Session, user_id: uuid.UUID) -> User | None:
    user = await session.get(User, user_id)
    if user and (user.cookies is None or user.cookies <= 0):
        return None
    return user

async def get_cookie_by_name(session: Session, name: str) -> Cookie | None:
    statement = select(Cookie).where(Cookie.name == name)
    result = await session.exec(statement)
    return result.first()

async def create_new_cookie(session: Session, cookie_data: Cookie) -> Cookie:
    session.add(cookie_data)
    # The commit for creating a cookie might be better handled in a service layer
    # or a transactional block with user update.
    # For now, let's assume it's part of a larger transaction or committed by the caller.
    # await session.commit() # Commit if this function is responsible for it
    # await session.refresh(cookie_data) # Refresh if committed
    return cookie_data

# Potentially a service-like function that combines operations
async def spend_user_cookie_and_create_new_db_cookie(
    session: Session, user_id: uuid.UUID, new_cookie_obj: Cookie
) -> tuple[User | None, Cookie | None]:
    user = await session.get(User, user_id)
    if not user:
        return None, None
    if user.cookies is None or user.cookies <= 0:
        return user, None

    user.cookies -= 1
    session.add(user)
    session.add(new_cookie_obj)
    # Commit is handled in the API route after this function returns, as per original logic.
    # await session.commit() 
    # await session.refresh(user)
    # await session.refresh(new_cookie_obj)
    return user, new_cookie_obj

# 将cookie的inused设置为Fasle
async def set_cookie_inused_to_false(session: Session, cookie_name: str) -> Cookie | None:
    result = await session.exec(select(Cookie).where(Cookie.name == cookie_name))
    cookie = result.first()
    if cookie:
        cookie.inused = False
        session.add(cookie)
        await session.commit()
        await session.refresh(cookie)
    return cookie

# 将cookie的inused设置为True
async def set_cookie_inused_to_true(session: Session, cookie_name: str) -> Cookie | None:
    result = await session.exec(select(Cookie).where(Cookie.name == cookie_name))
    cookie = result.first()
    if cookie:
        cookie.inused = True
        session.add(cookie)
        await session.commit()
        await session.refresh(cookie)
    return cookie
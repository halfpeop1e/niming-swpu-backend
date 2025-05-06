import uuid
from typing import Any

from sqlmodel import Session, select

from app.core.security import get_password_hash, verify_password
from app.models import Item, ItemCreate, User, UserCreate, UserUpdate, DefaultCard, AddReplyCard, Cookie

#向数据库中添加新卡片的函数实现
def create_card(*, session: Session, card_in: DefaultCard) -> DefaultCard:
    """
    Adds a new card record to the database.
    Assumes card_in is a pre-validated DefaultCard instance.
    """
    # 直接使用传递进来的 DefaultCard 实例
    db_card = card_in
    session.add(db_card)
    session.commit()
    session.refresh(db_card)
    return db_card

#向数据库中添加新回复卡片的函数实现
def create_reply_card(*, session: Session, reply_card_in: AddReplyCard) -> AddReplyCard:
    """
    这个函数是向数据库中添加新回复卡片的函数实现
    """
    db_reply_card = reply_card_in
    session.add(db_reply_card)
    session.commit()
    session.refresh(db_reply_card)
    return db_reply_card


#向数据库中添加新用户的函数实现
def create_user(*, session: Session, user_create: UserCreate) -> User:
    db_obj = User.model_validate(
        user_create, update={"hashed_password": get_password_hash(user_create.password)}
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj

#这个函数会获取用户输入的明文密码 (password)
#和从数据库中读取的该用户的哈希密码 (db_user.hashed_password)
def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> Any:
    user_data = user_in.model_dump(exclude_unset=True)
    extra_data = {}
    if "password" in user_data:
        password = user_data["password"]
        hashed_password = get_password_hash(password)
        extra_data["hashed_password"] = hashed_password
    db_user.sqlmodel_update(user_data, update=extra_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user

#更新用户的cookies
def update_user_cookies(*, session: Session, db_user: User, cookies: int) -> Any:
    db_user.cookies = cookies
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user

def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    session_user = session.exec(statement).first()
    return session_user


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    db_user = get_user_by_email(session=session, email=email)
    if not db_user:
        return None
    if not verify_password(password, db_user.hashed_password):
        return None
    return db_user


def create_item(*, session: Session, item_in: ItemCreate, owner_id: uuid.UUID) -> Item:
    db_item = Item.model_validate(item_in, update={"owner_id": owner_id})
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item

def get_user_for_cookie_operation(session: Session, user_id: uuid.UUID) -> User | None:
    user = session.get(User, user_id) # session.get is efficient for PK lookup
    if user and (user.cookies is None or user.cookies <= 0):
        return None # Or raise a specific exception
    return user

def get_cookie_by_name(session: Session, name: str) -> Cookie | None:
    statement = select(Cookie).where(Cookie.name == name)
    return session.exec(statement).first()

def create_new_cookie(session: Session, cookie_data: Cookie) -> Cookie:
    session.add(cookie_data)
    # The commit for creating a cookie might be better handled in a service layer
    # or a transactional block with user update.
    # For now, let's assume it's part of a larger transaction.
    return cookie_data

# Potentially a service-like function that combines operations
def spend_user_cookie_and_create_new_db_cookie(
    session: Session, user_id: uuid.UUID, new_cookie_obj: Cookie
) -> tuple[User | None, Cookie | None]:
    user = session.get(User, user_id)
    if not user:
        return None, None # User not found
    if user.cookies is None or user.cookies <= 0:
        return user, None # Insufficient cookies

    user.cookies -= 1
    session.add(user)
    session.add(new_cookie_obj)
    # Commit happens after this function returns, in the API route
    return user, new_cookie_obj

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import col, delete, func, select

from app import crud
from app.api.deps import (
    CurrentUser,
    AsyncSessionDep,
    get_current_active_superuser,
    RedisClient,
)
from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.models import (
    Item,
    Message,
    UpdatePassword,
    User,
    UserCreate,
    UserPublic,
    UserRegister,
    UsersPublic,
    UserUpdate,
    UserUpdateMe,
)
from app.utils import generate_new_account_email, send_email
#######################################记录用户管理侧发生的事件
# user_number = 0
router = APIRouter(prefix="/users", tags=["users"])

SIGNUP_COUNTER_KEY = "signup_number"
TOTAL_API_CALLS_KEY = "total_api_calls" # Key for total API calls
######################该页面定义了用户管理相关的接口以及实现
@router.get(
    "/",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UsersPublic,
)
async def read_users(session: AsyncSessionDep, redis: RedisClient, skip: int = 0, limit: int = 100) -> Any:
    await redis.incr(TOTAL_API_CALLS_KEY)
    """
    Retrieve users.
    """

    count_statement = select(func.count()).select_from(User)
    count_result = await session.exec(count_statement)
    count = count_result.one()

    statement = select(User).offset(skip).limit(limit)
    users_result = await session.exec(statement)
    users = users_result.all()
    return UsersPublic(data=users, count=count)

#创建用户的代码实现
@router.post(
    "/", dependencies=[Depends(get_current_active_superuser)], response_model=UserPublic
)
async def create_user(*, session: AsyncSessionDep, user_in: UserCreate, redis: RedisClient) -> Any:
    await redis.incr(TOTAL_API_CALLS_KEY)
    """
    Create new user.
    """
    user = await crud.get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )

    user_created = await crud.create_user(session=session, user_create=user_in)
    await redis.incr(SIGNUP_COUNTER_KEY)

    if settings.emails_enabled and user_in.email:
        email_data = generate_new_account_email(
            email_to=user_in.email, username=user_in.email, password=user_in.password
        )
        send_email(
            email_to=user_in.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
    return user_created

#更新用户信息
@router.patch("/me", response_model=UserPublic)
async def update_user_me(
    *, session: AsyncSessionDep, user_in: UserUpdateMe, current_user: CurrentUser, redis: RedisClient
) -> Any:
    await redis.incr(TOTAL_API_CALLS_KEY)
    """
    Update own user.
    """

    if user_in.email:
        existing_user = await crud.get_user_by_email(session=session, email=user_in.email)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=409, detail="User with this email already exists"
            )
    user_data = user_in.model_dump(exclude_unset=True)
    current_user.sqlmodel_update(user_data)
    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)
    return current_user

#更新密码
@router.patch("/me/password", response_model=Message)
async def update_password_me(
    *, session: AsyncSessionDep, body: UpdatePassword, current_user: CurrentUser, redis: RedisClient
) -> Any:
    await redis.incr(TOTAL_API_CALLS_KEY)
    """
    Update own password.
    """
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect password")
    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=400, detail="New password cannot be the same as the current one"
        )
    hashed_password = get_password_hash(body.new_password)
    current_user.hashed_password = hashed_password
    session.add(current_user)
    await session.commit()
    return Message(message="Password updated successfully")


@router.get("/me", response_model=UserPublic)
async def read_user_me(current_user: CurrentUser, redis: RedisClient) -> Any:
    await redis.incr(TOTAL_API_CALLS_KEY)
    """
    Get current user.
    """
    return current_user

#删除用户
@router.delete("/me", response_model=Message)
async def delete_user_me(session: AsyncSessionDep, current_user: CurrentUser, redis: RedisClient) -> Any:
    await redis.incr(TOTAL_API_CALLS_KEY)
    """
    Delete own user.
    """
    if current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="Super users are not allowed to delete themselves"
        )
    await session.delete(current_user)
    await session.commit()
    return Message(message="User deleted successfully")

#注册用户的接口以及实现
@router.post("/signup", response_model=UserPublic)
async def register_user(session: AsyncSessionDep, user_in: UserRegister, redis: RedisClient) -> Any:
    await redis.incr(TOTAL_API_CALLS_KEY)
    """
    Create new user without the need to be logged in.
    """
    user = await crud.get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system",
        )
    user_create = UserCreate.model_validate(user_in)
    user_created = await crud.create_user(session=session, user_create=user_create)
    await redis.incr(SIGNUP_COUNTER_KEY)
    return user_created


@router.get("/{user_id}", response_model=UserPublic)
async def read_user_by_id(
    user_id: uuid.UUID, session: AsyncSessionDep, current_user: CurrentUser, redis: RedisClient
) -> Any:
    await redis.incr(TOTAL_API_CALLS_KEY)
    """
    Get a specific user by id.
    """
    user = await session.get(User, user_id)
    if user == current_user:
        return user
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="The user doesn't have enough privileges",
        )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch(
    "/{user_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UserPublic,
)
async def update_user(
    *,
    session: AsyncSessionDep,
    user_id: uuid.UUID,
    user_in: UserUpdate,
    redis: RedisClient
) -> Any:
    await redis.incr(TOTAL_API_CALLS_KEY)
    """
    Update a user.
    """

    db_user = await session.get(User, user_id)
    if not db_user:
        raise HTTPException(
            status_code=404,
            detail="The user with this id does not exist in the system",
        )
    if user_in.email:
        existing_user = await crud.get_user_by_email(session=session, email=user_in.email)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(
                status_code=409, detail="User with this email already exists"
            )

    db_user = await crud.update_user(session=session, db_user=db_user, user_in=user_in)
    return db_user


@router.delete("/{user_id}", dependencies=[Depends(get_current_active_superuser)])
async def delete_user(
    session: AsyncSessionDep, current_user: CurrentUser, user_id: uuid.UUID, redis: RedisClient
) -> Message:
    await redis.incr(TOTAL_API_CALLS_KEY)
    """
    Delete a user.
    """
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user == current_user:
        raise HTTPException(
            status_code=403, detail="Super users are not allowed to delete themselves"
        )
    statement = delete(Item).where(col(Item.owner_id) == user_id)
    await session.exec(statement)  # type: ignore
    await session.delete(user)
    await session.commit()
    return Message(message="User deleted successfully")

import random
import string
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from loguru import logger
from app.models import Cookie, User, Message, CookieResponse, CookieUse
from app import crud
from app.api.deps import CurrentUser, SessionDep

router = APIRouter(prefix="/cookies",tags=["cookies"])

@router.get("/addcookie", response_model=Message)
def add_cookie(session:SessionDep,current_user:CurrentUser):
    user_id_from_token = current_user.id

    generated_cookie_name = ""
    while True:
        temp_name = ''.join(random.choices(string.ascii_letters + string.digits, k=7))
        existing_cookie = crud.get_cookie_by_name(session=session, name=temp_name)
        if not existing_cookie:
            generated_cookie_name = temp_name
            break

    now_server_time = datetime.utcnow()
    formatted_time = now_server_time.strftime("%Y-%m-%d-%H:%M")

    new_cookie_data_obj = Cookie(
        name=generated_cookie_name,
        time=formatted_time,
        isbanned=False,
        inused=False,
        id=user_id_from_token
    )

    updated_user, created_cookie_obj = crud.spend_user_cookie_and_create_new_db_cookie(
        session=session,
        user_id=user_id_from_token,
        new_cookie_obj=new_cookie_data_obj
    )

    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    if not created_cookie_obj:
        return Message(message="cookies点数不足")

    try:
        session.commit()
        session.refresh(updated_user)
        session.refresh(created_cookie_obj)
        logger.info(f"User {user_id_from_token} added cookie (Name: {created_cookie_obj.name}, UserID via FK: {created_cookie_obj.id}). Remaining cookies: {updated_user.cookies}")
        return Message(message=f"Cookie '{created_cookie_obj.name}' 添加成功，剩余cookies: {updated_user.cookies}")
    except Exception as e:
        logger.exception(f"Error committing to database: {e}")
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="添加Cookie失败，请稍后再试")

# 查询cookie,通过user.id，也就是uuid去查询
@router.get("/getcookie", response_model=CookieResponse)
def get_cookie(session:SessionDep,current_user:CurrentUser):
    user_id_from_token = current_user.id
    # 通过user.id去查询cookie
    cookies = session.exec(select(Cookie).where(Cookie.id==user_id_from_token)).all()
    return CookieResponse(data=cookies)

# 客户端携带cookie的name以及自己的token去启用name对应的cookie
@router.post("/use_cookie", response_model=Message)
def use_cookie(session:SessionDep,current_user:CurrentUser,cookie_use:CookieUse):
    user_id_from_token = current_user.id
    # 通过user.id去查询cookie
    cookies = session.exec(select(Cookie).where(Cookie.id==user_id_from_token)).all()
    # 如果有cookies的inused为True，则将inused设置为False
    for cookie in cookies:
        if cookie.inused:
            crud.set_cookie_inused_to_false(session=session, cookie_name=cookie.name)
    # 将传入的cookie_use.name设置为True
    crud.set_cookie_inused_to_true(session=session, cookie_name=cookie_use.name)
    logger.info(f"User {user_id_from_token} used cookie (Name: {cookie_use.name}).")
    return Message(message="Cookie启用成功")






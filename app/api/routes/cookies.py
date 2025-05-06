import random
import string
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from loguru import logger
from app.models import Cookie, User, Message
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





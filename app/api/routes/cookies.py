import random
import string
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from loguru import logger
from app.models import Cookie, User, Message, CookieResponse, CookieUse, GetUserCookieNum
from app import crud
from app.api.deps import CurrentUser, AsyncSessionDep

router = APIRouter(prefix="/cookies",tags=["cookies"])
TOTAL_API_CALLS_KEY = "total_api_calls"

@router.get("/addcookie", response_model=Message)
async def add_cookie(session:AsyncSessionDep,current_user:CurrentUser, ):
    
    user_id_from_token = current_user.id

    generated_cookie_name = ""
    while True:
        temp_name = ''.join(random.choices(string.ascii_letters + string.digits, k=7))
        existing_cookie = await crud.get_cookie_by_name(session=session, name=temp_name)
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

    updated_user, created_cookie_obj = await crud.spend_user_cookie_and_create_new_db_cookie(
        session=session,
        user_id=user_id_from_token,
        new_cookie_obj=new_cookie_data_obj
    )

    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    if not created_cookie_obj:
        return Message(message="cookies点数不足")

    await session.commit()
    await session.refresh(updated_user)
    await session.refresh(created_cookie_obj)

    try:
        logger.info(f"User {user_id_from_token} added cookie (Name: {created_cookie_obj.name}, UserID via FK: {created_cookie_obj.id}). Remaining cookies: {updated_user.cookies}")
        return Message(message=f"Cookie '{created_cookie_obj.name}' 添加成功，剩余cookies: {updated_user.cookies}")
    except Exception as e:
        logger.exception(f"Error during cookie addition: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="添加Cookie失败，请稍后再试")

@router.get("/getcookie", response_model=CookieResponse)
async def get_cookie(session:AsyncSessionDep,current_user:CurrentUser, ):
    
    user_id_from_token = current_user.id
    result = await session.exec(select(Cookie).where(Cookie.id==user_id_from_token))
    cookies = result.all()
    return CookieResponse(data=cookies)

@router.post("/use_cookie", response_model=Message)
async def use_cookie(session:AsyncSessionDep,current_user:CurrentUser,cookie_use:CookieUse, ):
    
    user_id_from_token = current_user.id
    result = await session.exec(select(Cookie).where(Cookie.id==user_id_from_token))
    cookies = result.all()
    for cookie_item in cookies:
        if cookie_item.inused:
            await crud.set_cookie_inused_to_false(session=session, cookie_name=cookie_item.name)
    await crud.set_cookie_inused_to_true(session=session, cookie_name=cookie_use.name)
    logger.info(f"User {user_id_from_token} used cookie (Name: {cookie_use.name}).")
    return Message(message="Cookie启用成功")

@router.get("/getusercookienum",response_model=GetUserCookieNum)
async def get_user_cookie_num(session:AsyncSessionDep,current_user:CurrentUser, ):
    
    user_id_from_token = current_user.id
    result = await session.exec(select(User).where(User.id==user_id_from_token))
    user = result.first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return GetUserCookieNum(number=user.cookies if user.cookies is not None else 0)



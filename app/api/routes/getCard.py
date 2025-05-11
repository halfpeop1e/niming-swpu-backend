import uuid

from fastapi import APIRouter, Depends,HTTPException,Request, Query, File, UploadFile, Form, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from pydantic import BaseModel, Field, HttpUrl
from loguru import logger
from typing import Optional, Any, List
import hashlib
import os

from app import crud
from app.api.deps import AsyncSessionDep, CurrentUser, SessionDep, RedisClient
from app.models import AddReplyCard, AddReplyCard_Client, DefaultCard, DefaultCardResponse, Message, CardRequest, \
    AddCard, ReplyCardRequest, AddReplyCardResponse, CardRequest_New, LikeRequest, ReplyLike,ImageUploadResponse, \
    ImageData, ImageDataLinks, ImagePathInfo

##################该页面定义了获取聊天卡片信息的接口以及实现

router = APIRouter(prefix="/cards", tags=["cards"])
TOTAL_API_CALLS_KEY = "total_api_calls"

# --- Stress Test Endpoint ---
@router.get("/stress-test-cards", response_model=DefaultCardResponse)
async def get_stress_test_cards(
    session: AsyncSessionDep, 
):
    """
    压力测试的地方
    """
    # 记录API调用 (如果需要)
    # 从数据库获取cards
    statement = select(DefaultCard).where(DefaultCard.category=="time").offset(0)
    statement = statement.order_by(DefaultCard.time.desc())
    # 确保异步执行数据库查询
    result = await session.exec(statement) # <--- 使用 await
    cards = result.all()                   # <--- 获取结果
    return DefaultCardResponse(data=cards)
# --- End Stress Test Endpoint ---

# 请求话题卡片的接口
@router.post("/getcard", response_model=DefaultCardResponse)
async def get_card(session: AsyncSessionDep, request_data: CardRequest, redis: RedisClient):
    await redis.incr(TOTAL_API_CALLS_KEY)
    statement = select(DefaultCard).where(DefaultCard.category==request_data.category).offset(request_data.skip).limit(5)
    statement = statement.order_by(DefaultCard.time.desc())
    result = await session.exec(statement)
    cards = result.all()
    return DefaultCardResponse(data = cards)

@router.get("/getonecard/{number}", response_model=DefaultCardResponse)
async def get_onecard(number:int, session:AsyncSessionDep, redis: RedisClient):
    await redis.incr(TOTAL_API_CALLS_KEY)
    result = await session.exec(select(DefaultCard).where(DefaultCard.number == number))
    thecard = result.first()
    if not thecard:
        raise HTTPException(status_code=404, detail="卡片不存在")
    return DefaultCardResponse(data=[thecard])

# 请求最新的一个卡片，通过category去查询
@router.post("/getnewcard",response_model=DefaultCardResponse)
async def get_new_card(session:AsyncSessionDep,request_data:CardRequest_New, redis: RedisClient):
    await redis.incr(TOTAL_API_CALLS_KEY)
    statement = select(DefaultCard).where(DefaultCard.category==request_data.category).order_by(DefaultCard.time.desc()).limit(1)
    result = await session.exec(statement)
    card = result.first()
    return DefaultCardResponse(data = card)

# 请求回复卡片的内容
@router.post("/getreplycard",response_model=AddReplyCardResponse)
async def get_reply_card(session:AsyncSessionDep,request_data:ReplyCardRequest, redis: RedisClient):
    await redis.incr(TOTAL_API_CALLS_KEY)
    statement = select(AddReplyCard).where(AddReplyCard.number==request_data.number).offset(request_data.skip).limit(5)
    result = await session.exec(statement)
    cards = result.all()
    return AddReplyCardResponse(data = cards)

@router.post("/addcard",response_model=Message)
async def add_card(session:AsyncSessionDep,current_user: CurrentUser,request_data:AddCard, redis: RedisClient):
    await redis.incr(TOTAL_API_CALLS_KEY)
    logger.info(f"话题更新了一条信息: {request_data}")
    # request_data.imageUrls is Optional[List[ImagePathInfo]]
    logger.info(f"收到的图片信息对象列表: {request_data.imageUrls}")

    result = await session.exec(select(DefaultCard).order_by(DefaultCard.number.desc()))
    last_card = result.first()
    if last_card:
        new_number = last_card.number + 1
    else:
        new_number = 1
    logger.info(f"Calculated new card number: {new_number}")

    # 从 List[ImagePathInfo] 提取 List[str] (只包含 relativePath)
    image_relative_paths: Optional[List[str]] = None # Default to None (or [] if empty list is preferred over NULL in DB)
    if request_data.imageUrls: # Check if the list exists and is not empty
        paths = [
            img_info.relativePath 
            for img_info in request_data.imageUrls 
            if img_info and hasattr(img_info, 'relativePath') and img_info.relativePath
        ]
        if paths: # If we successfully extracted any paths
            image_relative_paths = paths
    
    logger.info(f"提取的图片相对路径列表 (用于数据库): {image_relative_paths}")

    try:
        new_card = DefaultCard(
            number=new_number,
            id=request_data.id,
            content=request_data.content,
            time=request_data.time,
            category=request_data.category,
            thumbs=0,  # Initialize thumbs, assuming 0 is the default for a new card
            imageUrls=image_relative_paths # Assign the extracted list of relative paths
        )
        logger.info(f"Created DefaultCard instance for DB: {new_card}")
        await crud.create_card(session=session, card_in=new_card)
        logger.info("Successfully called crud.create_card")
        return Message(message="发送成功")
    except Exception as e:
        logger.exception("Error occurred during card creation or saving:")
        raise

@router.post("/addreplycard",response_model=Message)
async def add_reply_card(session:AsyncSessionDep,current_user: CurrentUser,request_data:AddReplyCard_Client, redis: RedisClient):
    await redis.incr(TOTAL_API_CALLS_KEY)
    logger.info(f"Adding reply card. Request data: {request_data}")

    result = await session.exec(select(DefaultCard).where(DefaultCard.number==request_data.number))
    card = result.first()
    if not card: # Check if the parent card exists
        logger.warning(f"Parent card with number {request_data.number} not found.")
        # Consider returning a more specific error message or status code
        # For now, matching existing logic but HTTPException might be better.
        return Message(message="卡片不存在")
    
    # Process imageUrls from List[ImagePathInfo] to List[str]
    image_relative_paths: Optional[List[str]] = None
    if request_data.imageUrls: # Check if imageUrls list exists and is not empty
        logger.info(f"Received imageUrls for reply card: {request_data.imageUrls}")
        paths = [
            img_info.relativePath 
            for img_info in request_data.imageUrls 
            if img_info and hasattr(img_info, 'relativePath') and img_info.relativePath
        ]
        if paths:
            image_relative_paths = paths
        logger.info(f"Extracted relative paths for reply card DB: {image_relative_paths}")
    else:
        logger.info("No imageUrls provided for reply card.")

    new_reply_card = AddReplyCard(
        number=request_data.number, # This is the foreign key to DefaultCard.number
        id=request_data.id,
        content=request_data.content,
        time=request_data.time,
        reply=request_data.reply,
        thumbs=0, # Initialize thumbs
        imageUrls=image_relative_paths # Assign the processed list of relative paths
    )
    
    logger.info(f"Creating AddReplyCard instance for DB: {new_reply_card}")
    await crud.create_reply_card(session=session,reply_card_in=new_reply_card)
    # Original log, slightly updated to reflect potential images
    logger.info(f"User {request_data.id} added reply card (Parent Card Number: {request_data.number}), content: {request_data.content}, reply: {request_data.reply}, time: {request_data.time}, images: {image_relative_paths is not None}")
    return Message(message="回复卡片添加成功")


@router.post("/like")
async def toggle_like(data: LikeRequest, session: AsyncSessionDep, current_user: CurrentUser, request: Request, redis: RedisClient):
    await redis.incr(TOTAL_API_CALLS_KEY)
    user_id = current_user.id
    print("收到请求体：", await request.json())
    try:
        reply_uuid = uuid.UUID(str(data.reply_id))
    except ValueError:
        reply_uuid = None
    try:
        reply_int = int(data.reply_id)
    except ValueError:
        reply_int = None
    reply_card = None
    default_card = None
    if reply_uuid:
        result = await session.exec(
            select(AddReplyCard).where(AddReplyCard.number_primary == reply_uuid)
        )
        reply_card = result.first()
    if reply_int is not None:
        result = await session.exec(
            select(DefaultCard).where(DefaultCard.number == reply_int)
        )
        default_card = result.first()

    if not reply_card and not default_card:
        raise HTTPException(status_code=404, detail="未找到对应的回复或卡片")
    target_id = str(data.reply_id)
    if data.action == "like":
        result = await session.exec(
            select(ReplyLike).where(
                ReplyLike.reply_id == target_id,
                ReplyLike.user_id == user_id
            )
        )
        existing = result.first()
        if existing:
            raise HTTPException(status_code=400, detail="不能重复点赞")
        
        new_like = ReplyLike(reply_id=target_id, user_id=user_id)
        session.add(new_like)

        if reply_card:
            reply_card.thumbs = (reply_card.thumbs or 0) + 1
            session.add(reply_card)
        elif default_card:
            default_card.thumbs = (default_card.thumbs or 0) + 1
            session.add(default_card)
        
        await session.commit()
        return {"message": "点赞成功"}

    elif data.action == "unlike":
        result = await session.exec(
            select(ReplyLike).where(
                ReplyLike.reply_id == target_id,
                ReplyLike.user_id == user_id
            )
        )
        like_to_delete = result.first()

        if not like_to_delete:
            raise HTTPException(status_code=400, detail="未点赞，无法取消")
        
        await session.delete(like_to_delete)

        if reply_card:
            reply_card.thumbs = max((reply_card.thumbs or 0) - 1, 0)
            session.add(reply_card)
        elif default_card:
            default_card.thumbs = max((default_card.thumbs or 0) - 1, 0)
            session.add(default_card)
        
        await session.commit()
        return {"message": "取消点赞成功"}

    else:
        raise HTTPException(status_code=400, detail="无效操作类型")

@router.get("/like-status")
async def get_like_status(reply_id: str, session: AsyncSessionDep, current_user: CurrentUser, redis: RedisClient):
    await redis.incr(TOTAL_API_CALLS_KEY)
    user_id = current_user.id
    result = await session.exec(
        select(ReplyLike).where(
            ReplyLike.reply_id == reply_id,
            ReplyLike.user_id == user_id
        )
    )
    existing = result.first()

    return {"liked": bool(existing)}





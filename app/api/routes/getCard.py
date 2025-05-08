import uuid

from fastapi import APIRouter, Depends,HTTPException,Request
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from pydantic import BaseModel
from loguru import logger

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.models import AddReplyCard, AddReplyCard_Client, DefaultCard, DefaultCardResponse, Message, CardRequest, \
    AddCard, ReplyCardRequest, AddReplyCardResponse, CardRequest_New, LikeRequest, ReplyLike

##################该页面定义了获取聊天卡片信息的接口以及实现

router = APIRouter(prefix="/cards", tags=["cards"])

# 请求话题卡片的接口
@router.post("/getcard", response_model=DefaultCardResponse)
def get_card(session: SessionDep, request_data: CardRequest): # Receive request body
    # count_statement = select(func.count()).select_from(DefaultCard)#获取卡片总数
    # count = session.exec(count_statement).one()#执行查询

    # Use values from the request body model
    statement = select(DefaultCard).where(DefaultCard.category==request_data.category).offset(request_data.skip).limit(5)#获取卡片列表
    # 用时间来排序，时间越大的靠在前面
    statement = statement.order_by(DefaultCard.time.desc())
    cards = session.exec(statement).all()#执行查询
    return DefaultCardResponse(data = cards) #返回卡片列表

# 请求最新的一个卡片，通过category去查询
@router.post("/getnewcard",response_model=DefaultCardResponse)
def get_new_card(session:SessionDep,request_data:CardRequest_New):
    statement = select(DefaultCard).where(DefaultCard.category==request_data.category).order_by(DefaultCard.time.desc()).limit(1)
    card = session.exec(statement).first()
    return DefaultCardResponse(data = card)

# 请求回复卡片的内容
@router.post("/getreplycard",response_model=AddReplyCardResponse)
def get_reply_card(session:SessionDep,request_data:ReplyCardRequest):
    #通过number从AddReplyCard中查询所有number相同的卡片
    statement = select(AddReplyCard).where(AddReplyCard.number==request_data.number).offset(request_data.skip).limit(5)
    cards = session.exec(statement).all()
    return AddReplyCardResponse(data = cards)

@router.post("/addcard",response_model=Message)
def add_card(session:SessionDep,current_user: CurrentUser,request_data:AddCard):

    # 2. Log the received request_data
    logger.info(f"话题更新了一条信息: {request_data}")
    # logger.info(f"request_data.id: {request_data.id} (Type: {type(request_data.id)})")
    # logger.info(f"request_data.content: {request_data.content} (Type: {type(request_data.content)})")
    # logger.info(f"request_data.time: {request_data.time} (Type: {type(request_data.time)})")

    #通过数据库查询获取最后一条卡片的number
    last_card = session.exec(select(DefaultCard).order_by(DefaultCard.number.desc())).first()
    if last_card:
        new_number = last_card.number + 1
    else:
        new_number = 1

    logger.info(f"Calculated new card number: {new_number}")

    #创建新的卡片
    try:
        new_card = DefaultCard(number=new_number,id=request_data.id,content=request_data.content,
                               time=request_data.time,category=request_data.category)
        # 3. Log the created DefaultCard instance before passing to CRUD
        logger.info(f"Created DefaultCard instance: {new_card}")
        # logger.info(f"new_card.id: {new_card.id} (Type: {type(new_card.id)})")
        # logger.info(f"new_card.content: {new_card.content} (Type: {type(new_card.content)})")
        # logger.info(f"new_card.time: {new_card.time} (Type: {type(new_card.time)})")

        crud.create_card(session=session,card_in=new_card)
        logger.info("Successfully called crud.create_card")
        return Message(message="发送成功")
    except Exception as e:
        logger.exception("Error occurred during card creation or saving:") # Log any exception during creation/saving
        raise # Re-raise the exception to get the 500 error and traceback

@router.post("/addreplycard",response_model=Message)
def add_reply_card(session:SessionDep,current_user: CurrentUser,request_data:AddReplyCard_Client):
    #通过传回的number从DefaultCard中查询到对应的卡片的number
    card = session.exec(select(DefaultCard).where(DefaultCard.number==request_data.number)).first()
    #如果查询到卡片的number,将DefaultCard的number作为AddReplyCard的number
    if card:
        number = card.number
    else:
        return Message(message="卡片不存在")

    #创建新的回复卡片
    new_reply_card = AddReplyCard(number=number,id=request_data.id,
                                  content=request_data.content,time=request_data.time,
                                  reply=request_data.reply,thumbs=0)
    #将新的回复卡片添加到数据库中
    crud.create_reply_card(session=session,reply_card_in=new_reply_card)
    logger.info(f"User {request_data.id} added reply card (Number: {number}), content: {request_data.content}, reply: {request_data.reply}, time: {request_data.time}")
    return Message(message="回复卡片添加成功")


@router.post("/like")
async def toggle_like(data: LikeRequest, session: SessionDep, current_user: CurrentUser, request: Request):
    user_id = current_user.id  # 从 token 中获取的 user_id
    print("收到请求体：", await request.json())

    # 尝试将 reply_id 转为 UUID
    try:
        reply_uuid = uuid.UUID(str(data.reply_id))
    except ValueError:
        reply_uuid = None

    # 尝试将 reply_id 转为 int
    try:
        reply_int = int(data.reply_id)
    except ValueError:
        reply_int = None

    # 初始化查询结果
    reply_card = None
    default_card = None

    # 查找 AddReplyCard
    if reply_uuid:
        reply_card = session.exec(
            select(AddReplyCard).where(AddReplyCard.number_primary == reply_uuid)
        ).first()

    # 查找 DefaultCard
    if reply_int is not None:
        default_card = session.exec(
            select(DefaultCard).where(DefaultCard.number == reply_int)
        ).first()

    # 如果两者都找不到，抛出异常
    if not reply_card and not default_card:
        raise HTTPException(status_code=404, detail="未找到对应的回复或卡片")

    # 统一使用字符串存储 reply_id
    target_id = str(data.reply_id)

    if data.action == "like":
        # 检查是否已点赞
        existing = session.exec(
            select(ReplyLike).where(
                ReplyLike.reply_id == target_id,
                ReplyLike.user_id == user_id
            )
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="不能重复点赞")

        # 添加点赞记录
        session.add(ReplyLike(reply_id=target_id, user_id=user_id))

        # 增加 thumbs 计数
        if reply_card:
            reply_card.thumbs = (reply_card.thumbs or 0) + 1
        elif default_card:
            default_card.thumbs = (default_card.thumbs or 0) + 1

        session.commit()
        return {"message": "点赞成功"}

    elif data.action == "unlike":
        # 查找点赞记录
        like = session.exec(
            select(ReplyLike).where(
                ReplyLike.reply_id == target_id,
                ReplyLike.user_id == user_id
            )
        ).first()

        if not like:
            raise HTTPException(status_code=400, detail="未点赞，无法取消")

        # 删除点赞记录
        session.delete(like)

        # 减少 thumbs 计数
        if reply_card:
            reply_card.thumbs = max((reply_card.thumbs or 0) - 1, 0)
        elif default_card:
            default_card.thumbs = max((default_card.thumbs or 0) - 1, 0)

        session.commit()
        return {"message": "取消点赞成功"}

    else:
        raise HTTPException(status_code=400, detail="无效操作类型")
@router.get("/like-status")
def get_like_status(reply_id: str, session: SessionDep, current_user: CurrentUser):
    user_id = current_user.id  # 获取当前用户 ID

    # 查询是否已点赞
    existing = session.exec(
        select(ReplyLike).where(
            ReplyLike.reply_id == reply_id,
            ReplyLike.user_id == user_id
        )
    ).first()

    return {"liked": bool(existing)}


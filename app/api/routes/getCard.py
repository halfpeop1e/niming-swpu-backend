from fastapi import APIRouter, Depends
from sqlmodel import select
from pydantic import BaseModel
from loguru import logger

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.models import AddReplyCard, AddReplyCard_Client, DefaultCard, DefaultCardResponse, Message, CardRequest, AddCard, ReplyCardRequest, AddReplyCardResponse
##################该页面定义了获取聊天卡片信息的接口以及实现

router = APIRouter(prefix="/cards", tags=["cards"])

# 请求话题卡片的接口
@router.post("/getcard", response_model=DefaultCardResponse)
def get_card(session: SessionDep, request_data: CardRequest): # Receive request body
    # count_statement = select(func.count()).select_from(DefaultCard)#获取卡片总数
    # count = session.exec(count_statement).one()#执行查询

    # Use values from the request body model
    statement = select(DefaultCard).offset(request_data.skip).limit(5)#获取卡片列表
    cards = session.exec(statement).all()#执行查询
    return DefaultCardResponse(data = cards) #返回卡片列表

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
                               time=request_data.time)
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
    return Message(message="回复卡片添加成功")

        


from fastapi import APIRouter, Depends
from sqlmodel import select
from pydantic import BaseModel
from app.api.deps import SessionDep
from app.models import DefaultCard, DefaultCardResponse
##################该页面定义了获取聊天卡片信息的接口以及实现

# Define a Pydantic model for the request body
class CardRequest(BaseModel):
    skip: int = 0

router = APIRouter(prefix="/cards", tags=["cards"])

# Change to POST and update the function signature
@router.post("/getcard", response_model=DefaultCardResponse)
def get_card(session: SessionDep, request_data: CardRequest): # Receive request body
    # count_statement = select(func.count()).select_from(DefaultCard)#获取卡片总数
    # count = session.exec(count_statement).one()#执行查询

    # Use values from the request body model
    statement = select(DefaultCard).offset(request_data.skip).limit(5)#获取卡片列表
    cards = session.exec(statement).all()#执行查询
    return DefaultCardResponse(data = cards) #返回卡片列表


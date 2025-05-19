from datetime import timedelta
import os
from typing import Annotated, Any
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
import redis
from app import crud
# 导入依赖项，包括数据库会话、当前用户和超级用户检查
from app.api.deps import CurrentUser, AsyncSessionDep, get_current_active_superuser, get_redis, get_smtp
from app.core import security
from app.core.config import settings
from app.core.security import get_password_hash
# 导入数据模型
from app.models import Message, NewPassword, Token, UserPublic, VerifyCodeRequest
# 导入工具函数，用于生成 token、邮件内容和发送邮件
from smtplib import SMTP
from email.mime.text import MIMEText
from email.utils import formataddr
import random
from loguru import logger
router = APIRouter(tags=["smtp"])
# 获取验证码
@router.post("/smtp/get_verify_code")
async def get_verify_code(
    request: VerifyCodeRequest,
    smtp: Annotated[SMTP, Depends(get_smtp)],
    redis: Annotated[redis.Redis, Depends(get_redis)]
) -> Message:
    try:
        verify_code = random.randint(100000, 999999)
        msg = MIMEText(f"欢迎使用论坛，验证码的有效时间为10分钟，您的验证码是：{verify_code}", "plain", "utf-8")
        msg["From"] = settings.MAIL_FROM
        msg["To"] = request.email
        msg["Subject"] = "验证码"
        
        logger.info(f"准备发送验证码到邮箱: {request.email}")
        logger.info(f"发件人: {settings.MAIL_FROM}")
        
        await redis.set(f"verify_code:{request.email}", verify_code, ex=600)
        smtp.send_message(msg)
        
        logger.info(f"验证码发送成功: {request.email}")
        return Message(message=f"验证码已发送")
    except Exception as e:
        logger.error(f"发送验证码失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"发送验证码失败: {str(e)}")

# 重设密码的验证码
@router.post("/smtp/reset_password_verify_code")
async def reset_password_verify_code(
    request: VerifyCodeRequest,
    smtp: Annotated[SMTP, Depends(get_smtp)],
    redis: Annotated[redis.Redis, Depends(get_redis)]
) -> Message:
    try:
        verify_code = random.randint(100000, 999999)
        msg = MIMEText(f"重设密码的验证码的有效时间为10分钟，您的验证码是：{verify_code}", "plain", "utf-8")
        msg["From"] = settings.MAIL_FROM
        msg["To"] = request.email
        msg["Subject"] = "重设密码验证码"
        
        logger.info(f"准备发送重设密码验证码到邮箱: {request.email}")
        logger.info(f"发件人: {settings.MAIL_FROM}")
        
        await redis.set(f"reset_password_verify_code:{request.email}", verify_code, ex=600)
        smtp.send_message(msg)
        
        logger.info(f"重设密码验证码发送成功: {request.email}")
        return Message(message=f"验证码已发送")
    except Exception as e:
        logger.error(f"发送重设密码验证码失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"发送重设密码验证码失败: {str(e)}")

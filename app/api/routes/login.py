from datetime import timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm

from app import crud
# 导入依赖项，包括数据库会话、当前用户和超级用户检查
from app.api.deps import CurrentUser, SessionDep, get_current_active_superuser
from app.core import security
from app.core.config import settings
from app.core.security import get_password_hash
# 导入数据模型
from app.models import Message, NewPassword, Token, UserPublic
# 导入工具函数，用于生成 token、邮件内容和发送邮件
from app.utils import (
    generate_password_reset_token,
    generate_reset_password_email,
    send_email,
    verify_password_reset_token,
)
######################该页面定义了登录和通过token验证的接口以及实现
# 创建一个新的 API 路由器，并标记所有路由属于 "login" 标签
router = APIRouter(tags=["login"])


@router.post("/login/access-token")
def login_access_token(
    session: SessionDep, # 依赖注入：获取数据库会话
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()] # 依赖注入：获取 OAuth2 表单数据 (username, password)
) -> Token:
    """
    OAuth2 兼容的 token 登录接口。
    接收用户名和密码，验证成功后返回一个 access token。
    """
    # 使用 email (form_data.username) 和 password 进行认证
    user = crud.authenticate(
        session=session, email=form_data.username, password=form_data.password
    )
    if not user:
        # 如果认证失败（邮箱或密码错误），抛出 400 错误
        raise HTTPException(status_code=400, detail="邮箱或密码错误")
    elif not user.is_active:
        # 如果用户被禁用，抛出 400 错误
        raise HTTPException(status_code=400, detail="无效用户")
    # 从配置中读取 access token 的过期时间
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    # 创建 access token
    return Token(
        access_token=security.create_access_token(
            user.id, expires_delta=access_token_expires
        )
    )


@router.post("/login/test-token", response_model=UserPublic)
def test_token(current_user: CurrentUser) -> Any:
    """
    测试 access token 是否有效。
    需要请求头中带有有效的 Bearer token。
    """
    # current_user 依赖项会自动验证 token 并返回对应的用户对象
    # 如果 token 无效或过期，依赖项会抛出异常
    return current_user


@router.post("/password-recovery/{email}")
def recover_password(email: str, session: SessionDep) -> Message:
    """
    密码恢复接口。
    向指定邮箱发送包含密码重置 token 的邮件。
    """
    # 根据邮箱查找用户
    user = crud.get_user_by_email(session=session, email=email)

    if not user:
        # 如果用户不存在，抛出 404 错误
        raise HTTPException(
            status_code=404,
            detail="该邮箱对应的用户不存在。",
        )
    # 生成密码重置 token
    password_reset_token = generate_password_reset_token(email=email)
    # 生成密码重置邮件的内容（主题和 HTML 正文）
    email_data = generate_reset_password_email(
        email_to=user.email, email=email, token=password_reset_token
    )
    # 发送邮件
    send_email(
        email_to=user.email,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    # 返回成功消息
    return Message(message="密码恢复邮件已发送")


@router.post("/reset-password/")
def reset_password(session: SessionDep, body: NewPassword) -> Message:
    """
    重置密码接口。
    使用有效的 token 和新密码来更新用户密码。
    """
    # 验证密码重置 token 并获取对应的邮箱
    email = verify_password_reset_token(token=body.token)
    if not email:
        # 如果 token 无效或过期，抛出 400 错误
        raise HTTPException(status_code=400, detail="无效的 token")
    # 根据邮箱查找用户
    user = crud.get_user_by_email(session=session, email=email)
    if not user:
        # 如果用户不存在，抛出 404 错误
        raise HTTPException(
            status_code=404,
            detail="该邮箱对应的用户不存在。",
        )
    elif not user.is_active:
        # 如果用户被禁用，抛出 400 错误
        raise HTTPException(status_code=400, detail="无效用户")
    # 对新密码进行哈希处理
    hashed_password = get_password_hash(password=body.new_password)
    # 更新用户的哈希密码
    user.hashed_password = hashed_password
    # 将更改添加到数据库会话
    session.add(user)
    # 提交事务，保存更改
    session.commit()
    # 返回成功消息
    return Message(message="密码更新成功")


@router.post(
    "/password-recovery-html-content/{email}",
    # 此路由需要当前用户是活跃的超级用户
    dependencies=[Depends(get_current_active_superuser)],
    response_class=HTMLResponse, # 指定响应类型为 HTML
)
def recover_password_html_content(email: str, session: SessionDep) -> Any:
    """
    获取密码恢复邮件的 HTML 内容（仅限超级用户）。
    用于预览或测试邮件模板。
    """
    # 根据邮箱查找用户
    user = crud.get_user_by_email(session=session, email=email)

    if not user:
        # 如果用户不存在，抛出 404 错误
        raise HTTPException(
            status_code=404,
            detail="该用户名的用户不存在。", # 注意：这里的 detail 信息可能是笔误，应为"邮箱"而非"用户名"
        )
    # 生成密码重置 token
    password_reset_token = generate_password_reset_token(email=email)
    # 生成邮件内容
    email_data = generate_reset_password_email(
        email_to=user.email, email=email, token=password_reset_token
    )

    # 直接返回 HTML 内容，并将邮件主题放在响应头中
    return HTMLResponse(
        content=email_data.html_content, headers={"subject:": email_data.subject}
    )


@router.post("/login/verify-token", response_model=Message)
def verify_token(
    current_user: CurrentUser, # This dependency handles token verification
) -> Message:
    """
    Verifies the provided access token.
    Requires a valid Bearer token in the Authorization header.
    Returns a success message if the token is valid and the user is active.
    """
    # If the code reaches here, it means the CurrentUser dependency
    # successfully validated the token and retrieved an active user.
    return Message(message="登录成功")

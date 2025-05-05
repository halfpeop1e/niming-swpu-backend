from collections.abc import Generator
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel import Session

from app.core import security
from app.core.config import settings
from app.core.db import engine
from app.models import TokenPayload, User

# 创建一个 OAuth2PasswordBearer 实例，用于处理 Bearer Token 认证
# tokenUrl 指定了客户端获取 token 的端点路径
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)

# 依赖项函数：获取数据库会话
# 使用 'yield' 确保会话在使用后被正确关闭
def get_db() -> Generator[Session, None, None]:
    """
    数据库会话依赖项生成器。
    使用 Session(engine) 创建一个新的 SQLAlchemy 会话。
    通过 yield 将会话提供给路径操作函数或其他依赖项。
    请求处理完成后，会话会自动关闭。
    """
    with Session(engine) as session:
        yield session

# 类型注解：用于 FastAPI 依赖注入的数据库会话
# Annotated[Session, Depends(get_db)] 表示参数类型是 Session，
# 并且它的值应该通过调用 get_db() 函数来获取
SessionDep = Annotated[Session, Depends(get_db)]

# 类型注解：用于 FastAPI 依赖注入的 Token 字符串
# Annotated[str, Depends(reusable_oauth2)] 表示参数类型是 str，
# 并且它的值应该通过调用 reusable_oauth2 从请求头中提取 Bearer Token
TokenDep = Annotated[str, Depends(reusable_oauth2)]

# 依赖项函数：获取当前已认证的用户
def get_current_user(session: SessionDep, token: TokenDep) -> User:
    """
    解析并验证 token，然后从数据库中获取对应的用户。

    Args:
        session: 数据库会话，通过 SessionDep 注入。
        token: 从请求头中提取的 Bearer Token 字符串，通过 TokenDep 注入。

    Raises:
        HTTPException(403): 如果 token 无效或格式错误。
        HTTPException(404): 如果 token 中的用户 ID 在数据库中不存在。
        HTTPException(400): 如果用户已被禁用 (is_active=False)。

    Returns:
        从数据库中获取的 User 对象。
    """
    try:
        # 使用密钥和算法解码 JWT token
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        # 将解码后的 payload 转换为 TokenPayload 对象进行验证
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        # 如果解码失败或 Pydantic 模型验证失败，抛出 403 错误
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无法验证凭据",
        )
    # 从数据库中根据 token 中的 subject (用户 ID) 获取用户对象
    user = session.get(User, token_data.sub)
    if not user:
        # 如果数据库中找不到该用户，抛出 404 错误
        raise HTTPException(status_code=404, detail="用户未找到")
    if not user.is_active:
        # 如果用户已被禁用，抛出 400 错误
        raise HTTPException(status_code=400, detail="无效用户")
    # 返回有效的用户对象
    return user

# 类型注解：用于 FastAPI 依赖注入的当前用户对象
# Annotated[User, Depends(get_current_user)] 表示参数类型是 User，
# 并且它的值应该通过调用 get_current_user() 函数来获取
CurrentUser = Annotated[User, Depends(get_current_user)]

# 依赖项函数：获取当前已认证且具有超级用户权限的用户
def get_current_active_superuser(current_user: CurrentUser) -> User:
    """
    检查当前用户是否是超级用户。

    依赖于 get_current_user 来获取当前用户。

    Args:
        current_user: 当前已认证的用户对象，通过 CurrentUser 注入。

    Raises:
        HTTPException(403): 如果当前用户不是超级用户。

    Returns:
        如果用户是超级用户，则返回该用户对象。
    """
    # 检查用户对象的 is_superuser 属性
    if not current_user.is_superuser:
        # 如果不是超级用户，抛出 403 错误
        raise HTTPException(
            status_code=403, detail="该用户没有足够的权限"
        )
    # 返回具有超级用户权限的用户对象
    return current_user

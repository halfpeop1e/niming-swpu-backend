from sqlmodel import Session, create_engine, select
from sqlalchemy.ext.asyncio import create_async_engine

from app import crud
from app.core.config import settings
from app.models import User, UserCreate
from loguru import logger

# The new asynchronous engine, now including pool_size and max_overflow
engine = create_async_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    pool_size=200,
    max_overflow=200
)

# If your previous engine had other parameters like echo=True, 
# you should add them here as well, for example:
# engine = create_async_engine(str(settings.SQLALCHEMY_DATABASE_URI), echo=True)

# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly
# for more details: https://github.com/fastapi/full-stack-fastapi-template/issues/28


def init_db(session: Session) -> None:
    # Tables should be created with Alembic migrations
    # But if you don't want to use migrations, create
    # the tables un-commenting the next lines
    # from sqlmodel import SQLModel

    # This works because the models are already imported and registered from app.models
    # SQLModel.metadata.create_all(engine)

    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    logger.info(f"settings.FIRST_SUPERUSER: {settings.FIRST_SUPERUSER}")
    logger.info(f"settings.FIRST_SUPERUSER_PASSWORD: {settings.FIRST_SUPERUSER_PASSWORD}")
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
        )
        user = crud.create_user(session=session, user_create=user_in)

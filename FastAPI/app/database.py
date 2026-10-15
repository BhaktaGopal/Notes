from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings
from app.models import Base


def create_engine(database_url: str | None = None) -> AsyncEngine:
    return create_async_engine(
        database_url or settings.database_url,
        echo=False,
        pool_pre_ping=True,
    )


def create_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )


async def create_db_schema(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def get_db_session(
    request: Request,
) -> AsyncIterator[AsyncSession]:
    session_factory = request.app.state.session_factory

    async with session_factory() as session:
        yield session


DBSession = Annotated[
    AsyncSession,
    Depends(get_db_session),
]
from collections.abc import AsyncIterator
from typing import Annotated
import jwt
from jwt.exceptions import  InvalidTokenError
from fastapi.security import OAuth2PasswordBearer
from fastapi import Request, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import Setting
from app.models import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl = "/auth/token")


async def get_session(request:Request) -> AsyncIterator[AsyncSession]:
    session_factory  = request.app.state.session_factory
    async with session_factory() as session:
        yield session

SessionDep = Annotated[AsyncSession,Depends(get_session)]
async def get_current_user(token:Annotated[str,Depends(oauth2_scheme)],
                           session:SessionDep) -> User:
    pass
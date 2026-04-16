from __future__ import annotations

import logging
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.admin_control import AdminAccount
from jwt_utils import create_admin_token

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
logger = logging.getLogger("lipi.backend.admin.auth")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

async def authenticate_admin(
    db: AsyncSession, 
    email: str, 
    password: str
) -> AdminAccount | None:
    """Check credentials and return the AdminAccount if valid."""
    result = await db.execute(
        select(AdminAccount).where(AdminAccount.email == email, AdminAccount.is_active == True)
    )
    admin = result.scalar_one_or_none()
    
    if not admin or not admin.password_hash:
        return None
    
    if not verify_password(password, admin.password_hash):
        return None
        
    return admin

from __future__ import annotations

import logging
import bcrypt as bcrypt_lib
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.admin_control import AdminAccount
from jwt_utils import create_admin_token

logger = logging.getLogger("lipi.backend.admin.auth")

def get_password_hash(password: str) -> str:
    return bcrypt_lib.hashpw(password.encode("utf-8"), bcrypt_lib.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt_lib.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except ValueError:
        logger.warning("Stored admin password hash is not valid bcrypt")
        return False

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

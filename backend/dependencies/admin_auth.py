from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from config import settings
from db.connection import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from models.admin_control import AdminAccount
from sqlalchemy import select

security = HTTPBearer()

async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> AdminAccount:
    """
    Dependency to validate 'ctrl' scope JWTs and return the AdminAccount.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        admin_id: str | None = payload.get("sub")
        is_ctrl: bool = payload.get("ctrl", False)
        
        if not admin_id or not is_ctrl:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid admin credentials",
            )
            
        result = await db.execute(
            select(AdminAccount).where(AdminAccount.id == admin_id, AdminAccount.is_active == True)
        )
        admin = result.scalar_one_or_none()
        
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Admin account not found or inactive",
            )
            
        return admin
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate admin credentials",
        )

async def super_admin_only(admin: AdminAccount = Depends(get_current_admin)):
    if admin.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin privileges required",
        )
    return admin

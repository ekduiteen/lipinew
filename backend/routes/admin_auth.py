from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from db.connection import get_db
from services.admin_auth import authenticate_admin
from jwt_utils import create_admin_token

router = APIRouter(prefix="/api/ctrl/auth", tags=["control-auth"])

class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str

class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    full_name: str

@router.post("/login", response_model=AdminLoginResponse)
async def login_admin(
    data: AdminLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    admin = await authenticate_admin(db, data.email, data.password)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    token = create_admin_token(admin_id=admin.id, scope=admin.role)
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": admin.role,
        "full_name": admin.full_name
    }

import asyncio
import sys
import os

# Ensure we can import from backend
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db.connection import SessionLocal
from services.admin_auth import get_password_hash
from models.admin_control import AdminAccount

async def bootstrap():
    email = input("Admin Email: ").strip()
    name = input("Admin Full Name: ").strip()
    password = input("Password: ").strip()
    
    async with SessionLocal() as db:
        hashed = get_password_hash(password)
        admin = AdminAccount(
            email=email,
            full_name=name,
            password_hash=hashed,
            role="super_admin"
        )
        db.add(admin)
        await db.commit()
        print(f"Successfully created Super Admin: {email}")

if __name__ == "__main__":
    asyncio.run(bootstrap())

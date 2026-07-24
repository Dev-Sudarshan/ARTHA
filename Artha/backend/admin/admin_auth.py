import os
import bcrypt
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import List

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from admin import admin_models as models
from db.database import get_db

security = HTTPBearer()

SECRET_KEY = os.getenv("ARTHA_ADMIN_SECRET", "dev-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8
DEV_ADMIN_EMAIL = os.getenv("ARTHA_DEV_ADMIN_EMAIL", "admin@artha.com")
DEV_ADMIN_PASSWORD = os.getenv("ARTHA_DEV_ADMIN_PASSWORD", "admin123")
DEV_ADMIN_ROLE = os.getenv("ARTHA_DEV_ADMIN_ROLE", "super_admin")
ENABLE_DEV_ADMIN = os.getenv("ARTHA_ENABLE_DEV_ADMIN", "1") != "0"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def create_access_token(data: dict, expires_delta: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_delta)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_dev_admin(email: str = DEV_ADMIN_EMAIL):
    """Local fallback admin used only when the admin DB is unavailable in dev."""
    if not ENABLE_DEV_ADMIN:
        return None
    return SimpleNamespace(
        id=0,
        email=email,
        role=DEV_ADMIN_ROLE,
        is_active=True,
        created_at=datetime.utcnow(),
    )


def verify_dev_admin_credentials(email: str, password: str) -> bool:
    return ENABLE_DEV_ADMIN and email == DEV_ADMIN_EMAIL and password == DEV_ADMIN_PASSWORD


def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> models.AdminUser:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    try:
        admin = db.query(models.AdminUser).filter(models.AdminUser.email == email).first()
    except (SQLAlchemyError, Exception):
        admin = None

    if not admin:
        admin = get_dev_admin(email)

    if not admin or not admin.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive admin")
    return admin


def require_roles(roles: List[str]):
    def _checker(admin: models.AdminUser = Depends(get_current_admin)) -> models.AdminUser:
        if admin.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return admin

    return _checker

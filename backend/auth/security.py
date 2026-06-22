import os
from datetime import datetime, timedelta
import bcrypt
import jwt
from fastapi import Request, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database.db import get_db_session
from backend.models.models import User, Role

# Configuration
SECRET_KEY = os.environ.get("SECRET_KEY", "SUPER_SECRET_KEY_FOR_ANALYZER_BI_PLATFORM_12345!")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day expiration

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login", auto_error=False)

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

def get_token_from_request(request: Request) -> str:
    # 1. Try header first
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1]
        
    # 2. Try cookie second (crucial for NiceGUI page routing and page loads)
    token_cookie = request.cookies.get("access_token")
    if token_cookie:
        return token_cookie
        
    # 3. Fallback to oauth2 scheme
    # Note: request.query_params can also contain token if needed
    return None

def get_current_user(request: Request, db: Session = Depends(get_db_session)) -> User:
    token = get_token_from_request(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
        
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
        
    user = db.query(User).filter_by(username=username).first()
    if user is None:
        raise credentials_exception
        
    return user

def require_role(required_role: str):
    def dependency(current_user: User = Depends(get_current_user)):
        # Admin bypasses all checks
        if current_user.role.name == "Admin":
            return current_user
        if current_user.role.name != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation forbidden. Required role: {required_role}"
            )
        return current_user
    return dependency

def require_permissions(required_permissions: list[str]):
    def dependency(current_user: User = Depends(get_current_user)):
        # Admin bypass
        if current_user.role.name == "Admin":
            return current_user
            
        user_permissions = current_user.role.permissions or []
        # If "all" is in permissions, skip check
        if "all" in user_permissions:
            return current_user
            
        for perm in required_permissions:
            if perm not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Operation forbidden. Missing permission: {perm}"
                )
        return current_user
    return dependency

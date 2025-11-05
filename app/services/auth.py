from datetime import datetime, timedelta
from jose import jwt,JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, status
from app.config import SECRET_KEY,ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

pwd_context = CryptContext(schemes=['bcrypt'],deprecated='auto')

#--------------------
# PASSWORD AND HASHING
#-----------------------

def hash_password(password: str)->str:
    return pwd_context.hash(password)

def verify_password(plain:str, hashed:str)->bool:
    return pwd_context.verify(plain,hashed)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
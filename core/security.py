from datetime import datetime, timedelta, timezone 
from sqlmodel import select, Session 
from core.database import get_session 
from models.users import User
from typing import Annotated
# CORRECCIÓN: status se importa de fastapi
from fastapi import Depends, status 
from fastapi.security import OAuth2PasswordBearer
from fastapi.exceptions import HTTPException 
from models.tokens import Token as DBToken
from core.database import SessionDep

from jose import JWTError, jwt
import bcrypt

from dotenv import load_dotenv
import os

# CORRECCIÓN: Importación clave para cargar relaciones
from sqlalchemy.orm import selectinload

load_dotenv()
SECRET_KEY= os.getenv('SECRET_KEY')
ALGORITHM= os.getenv('ALGORITHM')
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES')) 

outh2_scheme= OAuth2PasswordBearer(tokenUrl="api/auth/login") 

def hash_password(password: str) -> str:
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed_password.decode('utf-8') 

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ValueError:
        return False
    except Exception:
        return False


def encode_token(data:dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # CORRECCIÓN: Usar .timestamp() para el campo 'exp' del JWT
    to_encode.update({"exp": expire.timestamp()})
    
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token, expire

def decode_token(
    token: Annotated[str, Depends(outh2_scheme)], 
    session: SessionDep
) -> User:
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = data.get('username')
        
        if username is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The token data is incomplete (missing username)")
        
        # CORRECCIÓN CLAVE: Carga explícita de Status y Role para evitar errores de Lazy Loading
        statement = (
            select(User)
            .where(User.username == username)
            .options(selectinload(User.status))
            .options(selectinload(User.role)) 
        )
        user_db = session.exec(statement).first()
        user_db = session.exec(statement).first()
        
        if user_db is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
        # Validador de estado del usuario
        if user_db.status and user_db.status.name in ["Inactivo", "Suspendido"]: 
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"User is currently {user_db.status.name}. Contact your system manager.")
        
        # Validador si está eliminado (Soft Delete)
        if user_db.deleted:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User deleted. Please, contact your system manager") 
        
        # Comprobar si el token está activo en la base de datos
        db_token = session.exec(
            select(DBToken)
            .where(DBToken.token == token,
                   DBToken.user_id == user_db.id,
                   DBToken.status_token == True)
        ).first()

        if not db_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been invalidated or not found/active in database.")
        
        return user_db

    except JWTError as e: 
        print(f"JWT Error: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    except HTTPException:
        raise
    except Exception as e:
        # Esto te dará el error exacto en la consola si el 500 persiste
        print(f"FATAL ERROR IN DECODE_TOKEN: {e}") 
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                            detail="An unexpected error occurred while validating the token.")
from datetime import datetime, timedelta
from sqlmodel import select
from core.database import SessionDep
from models.users import User
from models.roles import Role 
from typing import Annotated
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from fastapi.exceptions import HTTPException
from models.tokens import Token as DBToken

from jose import JWTError, jwt
import bcrypt

from dotenv import load_dotenv
import os

load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')
try:
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', 30))
except (TypeError, ValueError):
    ACCESS_TOKEN_EXPIRE_MINUTES = 30


outh2_scheme = OAuth2PasswordBearer(tokenUrl="api/login") 

def hash_password(password: str) -> str:
    """Hashea una contraseña usando bcrypt."""

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed_password.decode('utf-8') 

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si una contraseña plana coincide con una hasheada."""
    try:
        
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ValueError:
       
        return False

def encode_token(data: dict):
    """Crea un token JWT a partir de un diccionario de datos."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token, expire
    
def decode_token(token: Annotated[str, Depends(outh2_scheme)], session: SessionDep):
    """
    Decodifica y valida un token JWT. 
    Retorna el objeto User si el token es válido y activo.
    """
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = data.get('username')
        
        if username is None:
            raise HTTPException(status_code=400, detail="The token data is incomplete")
        
        # Obtener usuario de la base de datos
        user_db = session.exec(select(User).where(User.username == username)).first()
        
        if user_db is None:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Verificar si el usuario ha sido marcado como eliminado
        if user_db.deleted: # <--- Usando el campo 'deleted' que añadiste
            raise HTTPException(status_code=403, detail="User disabled. Please, contact your system manager") 
        
        # Comprobar si el token está activo en la base de datos
        db_token = session.exec(
            select(DBToken)
            .where(DBToken.token == token, DBToken.user_id == user_db.id, DBToken.status_token == True)
        ).first()

        if not db_token:
            raise HTTPException(status_code=401, detail="Token has been invalidated or not found in database.")
        
        return user_db 

    except JWTError: # Recolección de errores específicos de JWT
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
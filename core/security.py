# core/security.py

from datetime import datetime, timedelta, timezone 
from sqlmodel import select
from typing import Annotated
from fastapi import Depends, status 
from fastapi.security import OAuth2PasswordBearer
from fastapi.exceptions import HTTPException 

from jose import JWTError, jwt
import bcrypt

from dotenv import load_dotenv
import os

# Importaciones de Modelos y Tipos
from models.users import User
from models.tokens import Token as DBToken # DBToken es el alias de tu modelo Token
from core.database import SessionDep

# Importación clave para cargar relaciones (SOLUCIÓN AL ERROR 500 DE LAZY LOADING)
from sqlalchemy.orm import selectinload 

load_dotenv()
SECRET_KEY= os.getenv('SECRET_KEY')
ALGORITHM= os.getenv('ALGORITHM')
# Asegúrate de que esta variable esté definida en tu .env y sea un entero
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES')) 

# Define el esquema de seguridad para Swagger/OpenAPI
outh2_scheme= OAuth2PasswordBearer(tokenUrl="api/auth/login") 

# ----------------------------------------------------------------------
# FUNCIONES DE CONTRASEÑA
# ----------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Hashea una contraseña utilizando bcrypt."""
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed_password.decode('utf-8') 

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña plana contra su versión hasheada."""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ValueError:
        return False
    except Exception:
        return False

# ----------------------------------------------------------------------
# FUNCIONES DE TOKEN (JWT)
# ----------------------------------------------------------------------

def encode_token(data:dict):
    """Crea y codifica un token JWT."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire.timestamp()})
    
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token, expire

def decode_token(
    token: Annotated[str, Depends(outh2_scheme)], 
    session: SessionDep
) -> User:
    """
    Decodifica el token, valida al usuario y sus permisos, y verifica la validez del token en DB.
    
    Esta función es usada como dependencia para proteger endpoints.
    """
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = data.get('username')
        
        if username is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                                detail="The token data is incomplete (missing username)")
        
        # 1. BÚSQUEDA DEL USUARIO (CON CARGA EXPLÍCITA DE RELACIONES)
        statement = (
            select(User)
            .where(User.username == username)
            .options(selectinload(User.status))
            .options(selectinload(User.role)) 
        )
        # ❗ Solo una ejecución del query
        user_db = session.exec(statement).first()
        
        if user_db is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
        # 2. VALIDACIONES DEL USUARIO
        # Validador si está eliminado (Soft Delete)
        if user_db.deleted:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, 
                                detail="User deleted. Please, contact your system manager") 
        
        # Validador de estado del usuario (usando la relación cargada 'status')
        if user_db.status and user_db.status.name in ["Inactivo", "Suspendido"]: 
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, 
                                detail=f"User is currently {user_db.status.name}. Contact your system manager.")
        
        # 3. COMPROBACIÓN DEL TOKEN EN LA BASE DE DATOS
        db_token = session.exec(
            select(DBToken)
            .where(DBToken.token == token,
                   # ✅ CORRECCIÓN FINAL: Usamos id_user, según tu modelo Token
                   DBToken.id_user == user_db.id,
                   DBToken.status_token == True)
        ).first()

        if not db_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                                detail="Token has been invalidated or not found/active in database.")
        
        return user_db

    except JWTError as e: 
        print(f"JWT Error (Invalid Token): {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail="Invalid or expired token")
    except HTTPException:
        # Permite que las excepciones de FastAPI suban sin ser capturadas
        raise
    except Exception as e:
        # Esto captura cualquier error fatal de DB (incluyendo si Token, Status o Role no están mapeados o DBToken.id_user no existe)
        print(f"FATAL ERROR IN DECODE_TOKEN: {e}") 
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                            detail="An unexpected error occurred while validating the token.")
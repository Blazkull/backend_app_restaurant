# core/security.py

from datetime import datetime, timedelta, timezone 
from sqlmodel import select
from typing import Annotated
from fastapi import Depends, status, HTTPException 
from fastapi.security import OAuth2PasswordBearer

from jose import JWTError, jwt
import bcrypt

from dotenv import load_dotenv
import os

# Importaciones de Modelos y Tipos
from models.users import User
from models.tokens import Token as DBToken 
from models.views import View # Necesario para buscar el recurso
from models.link_models import RoleViewLink # Necesario para el permiso
from core.database import SessionDep

from sqlalchemy.orm import selectinload 

load_dotenv()
SECRET_KEY= os.getenv('SECRET_KEY')
ALGORITHM= os.getenv('ALGORITHM')
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES')) 

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
    Decodifica el token, valida al usuario y sus relaciones, y verifica la validez del token en DB.
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
        user_db = session.exec(statement).first()
        
        if user_db is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
        # 2. VALIDACIONES DEL USUARIO
        if user_db.deleted or (user_db.status and user_db.status.name in ["Inactivo", "Suspendido"]): 
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, 
                                detail="User is deleted or inactive. Contact system manager.")
        
        # 3. COMPROBACIÓN DEL TOKEN EN LA BASE DE DATOS
        db_token = session.exec(
            select(DBToken)
            .where(DBToken.token == token,
                   DBToken.id_user == user_db.id,
                   DBToken.status_token == True)
        ).first()

        if not db_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                                detail="Token has been invalidated or not found/active in database.")
        
        return user_db

    except JWTError: 
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail="Invalid or expired token.")
    except HTTPException:
        raise
    except Exception as e:
        # Captura cualquier error de DB/carga
        print(f"FATAL ERROR IN DECODE_TOKEN: {e}") 
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                            detail="An unexpected error occurred while validating the token.")


# ----------------------------------------------------------------------
# DEPENDENCIA DE AUTORIZACIÓN (Permisos)
# ----------------------------------------------------------------------

def check_permission(view_path: str):
    """
    Dependencia de FastAPI para verificar si el usuario autenticado tiene acceso a una vista/path específico.
    """
    # 🚨 NOTA CLAVE: La función interna 'permission_verifier' tiene la indentación correcta aquí.
    def permission_verifier(
        current_user: User = Depends(decode_token), # Primero autentica y carga el usuario
        session: SessionDep = Depends(SessionDep)
    ):
        # 1. Buscar la Vista/Recurso en la DB por su PATH
        view_db = session.exec(
            select(View).where(View.path == view_path, View.deleted == False)
        ).first()
        
        # Si la vista no existe en la DB, es un recurso no controlado/registrado
        if not view_db:
             # Por defecto, denegamos el acceso a paths no registrados para máxima seguridad (Fail-Safe)
             raise HTTPException(
                 status_code=status.HTTP_403_FORBIDDEN, 
                 detail=f"Recurso no registrado o eliminado: {view_path}"
             )

        # 2. Verificar el Rol Principal del Usuario contra el Permiso
        permission_link = session.exec(
            select(RoleViewLink).where(
                RoleViewLink.id_role == current_user.id_role,
                RoleViewLink.id_view == view_db.id,
                RoleViewLink.enabled == True # El permiso debe estar activo
            )
        ).first()

        if not permission_link:
            # Si no se encuentra el permiso, denegar el acceso
            # Utilizamos la relación cargada 'role.name' para dar mejor feedback.
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail=f"Permiso denegado: Su rol ({current_user.role.name}) no tiene acceso a la vista '{view_db.name}'."
            )
        
        return True # Autorización exitosa

    return permission_verifier
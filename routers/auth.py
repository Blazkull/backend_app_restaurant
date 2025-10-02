from datetime import datetime, timezone
from fastapi import APIRouter, status, HTTPException
from sqlmodel import select
from core.database import SessionDep # Dependencia de sesión de la base de datos
from core.security import encode_token, verify_password # Funciones de seguridad
from models.users import User # Modelo de usuario
from models.roles import Role # Modelo de rol (para obtener el nombre del rol)
from schemas.users_schema import UserLogin # Schema de entrada del login
from models.tokens import Token as DBToken # Modelo de la tabla de tokens
from schemas.tokens_schema import AccessTokenResponse # Schema de respuesta
from sqlalchemy.exc import SQLAlchemyError # Para manejar errores de base de datos
from sqlalchemy.orm import selectinload 
# CORRECCIÓN: Uso correcto de APIRouter
router = APIRouter(prefix="/api/auth", tags=["AUTH"])

# Definición de la excepción de seguridad para consistencia
INVALID_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Credenciales inválidas (usuario/contraseña)",
    headers={"WWW-Authenticate": "Bearer"},
)

@router.post("/login", response_model=AccessTokenResponse, status_code=status.HTTP_200_OK)
def login_user(user_data: UserLogin, session: SessionDep):
    try:
        # --- 1. Búsqueda de Usuario y Rol con JOIN ---
        statement = (
            select(User, Role.name)
            .join(Role, User.id_role == Role.id)
            .where(User.username == user_data.username)
            # AÑADE ESTA LÍNEA para cargar la relación Status
            .options(selectinload(User.status)) 
        )
        result = session.exec(statement).first()
        
        if not result:
            raise INVALID_CREDENTIALS
        
        user_db, role_name = result
        
        # --- 2. Verificación de Contraseña y Estado ---

        # 2a. Verificación de Contraseña
        if not user_db.password or not verify_password(user_data.password, user_db.password):
            raise INVALID_CREDENTIALS

        # 2b. Verificación de Estado (incluye Soft Delete)
        if user_db.deleted:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User deleted. Please, contact your system manager") 
        
        # Asume que 'status' está cargado automáticamente o se accede vía ID
        if user_db.status and user_db.status.name in ["Inactivo", "Suspendido"]: 
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"User is currently {user_db.status.name}. Contact your system manager.")


        # --- 3. Lógica de Token (Invalidación y Creación) ---
        
        # Invalidar tokens existentes
        existing_tokens = session.exec(
            select(DBToken).where(DBToken.user_id == user_db.id, DBToken.status_token == True)
        ).all()
        
        for token_entry in existing_tokens:
            token_entry.status_token = False
            session.add(token_entry)
        
        # Generar Nuevo Token JWT
        payload = {
            "username": user_db.username, 
            "email": user_db.email,
            "user_id": user_db.id,
            "role_name": role_name
        }
        encoded_jwt, expires_at = encode_token(payload)

        # Almacenar el nuevo token en la base de datos
        new_token_db = DBToken(
            token=encoded_jwt,
            user_id=user_db.id,
            expiration=expires_at,
            status_token=True,
            date_token=datetime.now(timezone.utc)
        )
        session.add(new_token_db)
        
        session.commit()
        session.refresh(new_token_db)

    # Manejo de excepciones
    except HTTPException:
        session.rollback() # Asegurar rollback en HTTPException
        raise
    except SQLAlchemyError as e:
        session.rollback()
        print(f"ERROR DB EN LOGIN: {e}") 
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al gestionar la sesión de seguridad (DB).",
        )
    except Exception as e:
        session.rollback()
        print(f"ERROR INESPERADO EN LOGIN: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inesperado durante el login: {str(e)}",
        )
        
    # --- 4. Devolver Respuesta ---
    return {
        "access_token": encoded_jwt, 
        "token_type": "bearer",
        "role_name": role_name 
    }
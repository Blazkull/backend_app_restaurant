from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import ValidationError
from sqlmodel import select
from starlette.responses import Response

# Importaciones de Core
from core.database import SessionDep
from core.security import decode_token, hash_password, verify_password

# Importaciones de Modelos y Schemas
from models.users import User
from models.status import Status
from models.roles import Role 
from schemas.users_schema import UserRead, UserCreate, UserUpdate, PasswordUpdate

router = APIRouter(prefix="/users", tags=["Usuarios"])

# ----------------------------------------------------------------------
# ENDPOINT 1: LISTAR Y FILTRAR USUARIOS (GET /users/) -> SOLO ACTIVOS
# ----------------------------------------------------------------------

@router.get(
    "/", 
    response_model=List[UserRead], 
    summary="Listar y filtrar usuarios activos con paginación"
)
def read_users(
    session: SessionDep,
    
    # Paginación
    offset: int = Query(default=0, ge=0, description="Número de registros a omitir (offset)."),
    limit: int = Query(default=10, le=100, description="Máxima cantidad de usuarios a retornar (limit)."),
    
    # Filtrado por Estado (Mantienes Status ID para otros estados: Inactivo, Suspendido, etc.)
    status_id: Optional[int] = Query(default=None, description="Filtrar por ID de estado."),
    status_name: Optional[str] = Query(default=None, description="Filtrar por nombre del estado."),
    
    # Filtrado por Rol
    role_id: Optional[int] = Query(default=None, description="Filtrar por ID de rol principal."),
    role_name: Optional[str] = Query(default=None, description="Filtrar por nombre del rol (ej: 'Administrador', 'Cajero')."),

    # Búsqueda por Nombre de Usuario (parcial)
    username_search: Optional[str] = Query(default=None, description="Buscar por nombre de usuario (parcialmente).")

) -> List[UserRead]:
    """
    Lista usuarios permitiendo filtros y paginación, **excluyendo a los usuarios con deleted=True por defecto**.
    """
    
    query = select(User)
    
    # --- EXCLUSIÓN CLAVE: Excluir usuarios eliminados (deleted=False) ---
    query = query.where(User.deleted == False)
    # -------------------------------------------------------------------
    
    # Filtrar por ID de estado (otros estados)
    if status_id is not None:
        query = query.where(User.id_status == status_id)
        
    #Filtrar por Nombre del estado
    if status_name:
        # Usa .join() para relacionar User y Status
        query = query.join(Status, User.id_status == Status.id).where(Status.name.ilike(f"%{status_name}%"))
    
    # Filtrar por ID de Rol
    if role_id is not None:
        query = query.where(User.id_role == role_id)
    
    #Filtrar por rol Nombre (Usa ilike para búsqueda flexible)
    if role_name:
        # Usa .join() para relacionar User y Role
        query = query.join(Role, User.id_role == Role.id).where(Role.name.ilike(f"%{role_name}%"))
        
    # Filtrar por nombre de usuario
    if username_search:
        query = query.where(User.username.ilike(f"%{username_search}%"))
        
    # Aplicar Paginación
    query = query.offset(offset).limit(limit)
    
    users = session.exec(query).all()
    
    if not users and (offset > 0 or status_id or status_name or role_id or username_search):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontraron usuarios que coincidan con los criterios de búsqueda o paginación."
        )

    return users

# ----------------------------------------------------------------------
# ENDPOINT 2: LISTAR USUARIOS ELIMINADOS (GET /users/deleted) -> NUEVO
# ----------------------------------------------------------------------

@router.get(
    "/deleted", 
    response_model=List[UserRead], 
    summary="Listar usuarios marcados como eliminados (deleted=True)"
)
def read_deleted_users(
    session: SessionDep,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=10, le=100)
) -> List[UserRead]:
    """
    Lista solo los usuarios cuyo campo 'deleted' es True.
    """
    query = select(User).where(User.deleted == True).offset(offset).limit(limit)
    users = session.exec(query).all()
    
    if not users and offset > 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontraron usuarios eliminados en el rango de paginación."
        )
    
    return users


# ----------------------------------------------------------------------
# ENDPOINT 3: OBTENER USUARIO POR ID (GET /users/{user_id}) -> SOLO ACTIVOS
# ----------------------------------------------------------------------

@router.get("/{user_id}", response_model=UserRead, summary="Obtener un usuario por ID (excluye eliminados)", dependencies=[Depends(decode_token)])
def read_user(user_id: int, session: SessionDep):
    """
    Busca un usuario por su ID. Retorna 404 si no existe O si está marcado como eliminado.
    """
    try:
        # Filtrar por ID y por la bandera 'deleted'
        query = select(User).where(
            User.id == user_id, 
            User.deleted == False 
        )
        user_db = session.exec(query).first()
        
        if not user_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User doesn't exist or is deleted."
            )
            
        return user_db 
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving user: {str(e)}",
        )

# ----------------------------------------------------------------------
# ENDPOINT 4: CREAR USUARIO (POST /users/)
# ----------------------------------------------------------------------

@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED, summary="Crear un nuevo usuario", dependencies=[Depends(decode_token)])
def create_user(user_data: UserCreate, session: SessionDep):

    try:
        # 1. Validación de longitud de contraseña
        if len(user_data.password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="The password must be at least 6 characters."
            )
        
        # 2. Validar existencia de username y email
        if session.exec(select(User).where(User.username == user_data.username)).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered") 
        
        if session.exec(select(User).where(User.email == user_data.email)).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered") 
        
        # 3. Hashear contraseña y crear objeto User
        user_data_dict = user_data.model_dump(exclude_none=True)
        user_data_dict["password"] = hash_password(user_data.password)
        
        user = User.model_validate(user_data_dict) 

        # 4. Guardar
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    except HTTPException as http_exc:
        raise http_exc
    except ValidationError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid input data: {str(ve)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating user: {str(e)}",
        )

# ----------------------------------------------------------------------
# ENDPOINT 5: ACTUALIZAR USUARIO (PATCH /users/{user_id})
# ----------------------------------------------------------------------

@router.patch("/{user_id}", response_model=UserRead, status_code=status.HTTP_200_OK, summary="Actualizar datos de usuario (sin contraseña)", dependencies=[Depends(decode_token)])
def update_user( user_id: int, user_data: UserUpdate, session: SessionDep):

    try:
        user_db = session.get(User, user_id)
        if not user_db:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User doesn't exist")
        
        user_data_dict=user_data.model_dump(exclude_unset=True)

        # 1. Validar unicidad de username
        if "username" in user_data_dict and user_data_dict["username"] != user_db.username:
            if session.exec(select(User).where(User.username == user_data_dict["username"])).first():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
            
        # 2. Validar unicidad de email
        if "email" in user_data_dict and user_data_dict["email"] != user_db.email:
            if session.exec(select(User).where(User.email == user_data_dict["email"])).first():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
            
        # 3. Prevenir actualización de contraseña en este endpoint
        if "password" in user_data_dict:
            del user_data_dict["password"] 
            
        # 4. Manejar "undelete"
        if "deleted" in user_data_dict and user_data_dict["deleted"] == False and user_db.deleted == True:
            user_db.deleted_at = None # Quitar la fecha de eliminación si se está reactivando

        # 5. Actualizar
        user_db.sqlmodel_update(user_data_dict)
        user_db.updated_at = datetime.utcnow()
        session.add(user_db)
        session.commit()
        session.refresh(user_db)
        return user_db 
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while updating user: {str(e)}",
        )

# ----------------------------------------------------------------------
# ENDPOINT 6: ACTUALIZAR CONTRASEÑA (PATCH /users/{user_id}/password)
# ----------------------------------------------------------------------

@router.patch("/{user_id}/password", response_model=dict, status_code=status.HTTP_200_OK, summary="Actualizar solo la contraseña del usuario", dependencies=[Depends(decode_token)])
def update_user_password(user_id: int, password_update: PasswordUpdate, session: SessionDep):
    try:
        user_db = session.get(User, user_id)
        if not user_db:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User doesn't exist")
        
        new_password = password_update.password

        # 1. Verificar la longitud de la nueva contraseña
        if len(new_password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="The password must be at least 6 characters."
            )

        # 2. Verificar si la nueva contraseña es igual a la actual (hasheada)
        if verify_password(new_password, user_db.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="New password cannot be the same as the old password."
            )

        # 3. Hashear y guardar
        user_db.password = hash_password(new_password)
        user_db.updated_at = datetime.utcnow()
        session.add(user_db)
        session.commit()
        return {"message": f"User '{user_db.username}' has successfully updated their password"}
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while updating password: {str(e)}",
        )

# ----------------------------------------------------------------------
# ENDPOINT 7: ELIMINAR USUARIO (DELETE /users/{user_id}) - SOFT DELETE
# ----------------------------------------------------------------------

@router.delete(
    "/{user_id}", 
    status_code=status.HTTP_204_NO_CONTENT, 
    summary="Eliminación suave de un usuario (Soft Delete)", 
    dependencies=[Depends(decode_token)]
)
def delete_user(user_id: int, session: SessionDep):
    """
    Realiza una eliminación suave (Soft Delete) del usuario, 
    marcando 'deleted = True' y registrando la fecha de eliminación.
    """
    try:
        user_db = session.get(User, user_id)
        
        if not user_db:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
        # 1. Verificar si el usuario ya está marcado como eliminado
        if user_db.deleted == True:
            return Response(status_code=status.HTTP_204_NO_CONTENT)

        # 2. Implementar Soft Delete
        user_db.deleted = True # <-- Marcar como eliminado
        user_db.deleted_at = datetime.utcnow()
        
        session.add(user_db)
        session.commit()
        
        # 3. Retornar respuesta exitosa sin contenido (204)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during soft delete: {str(e)}",
        )
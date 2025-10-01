from fastapi import APIRouter, Depends, status, HTTPException
from sqlmodel import select
from datetime import datetime
from typing import List
from starlette.responses import Response

# Importa dependencias y modelos
from core.database import SessionDep
from core.security import decode_token 
from models.roles import Role 
from models.views import View
from models.link_models import RoleViewLink # <-- USANDO EL MODELO DE ENLACE
from schemas.roles_schema import RoleCreate, RoleRead, RoleUpdate
from schemas.role_view_link_schema import RoleViewUpdateStatus

router = APIRouter(
    prefix="/api/roles", 
    tags=["ROLES"], 
    dependencies=[Depends(decode_token)]
) 

# ----------------------------------------------------------------------
# ENDPOINT 1: LISTAR ROLES ACTIVOS (GET /roles)
# ----------------------------------------------------------------------

@router.get("", response_model=List[RoleRead], summary="Listar roles activos")
def list_roles(session: SessionDep):
    """Obtiene una lista de todos los roles activos (deleted=False)."""
    try:
        statement = select(Role).where(Role.deleted == False)
        return session.exec(statement).all()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al listar roles: {str(e)}")

# ----------------------------------------------------------------------
# ENDPOINT 2: CREAR ROL (POST /roles)
# ----------------------------------------------------------------------

@router.post("", response_model=RoleRead, status_code=status.HTTP_201_CREATED, summary="Crear nuevo rol y asignarle permisos por defecto")
def create_role(role_data: RoleCreate, session: SessionDep):
    """Crea un nuevo rol, valida unicidad, y le asigna todas las vistas con enabled=True."""
    try:
        # Validación de Unicidad (solo entre roles activos)
        existing_role = session.exec(
            select(Role).where(Role.name == role_data.name, Role.deleted == False)
        ).first()
        if existing_role:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ya existe un rol activo con el nombre: '{role_data.name}'." )

        # 1. Creación del Rol
        role_db = Role.model_validate(role_data.model_dump())
        role_db.created_at = datetime.utcnow()
        role_db.updated_at = datetime.utcnow()
        session.add(role_db)
        session.flush() # Obtiene el ID antes del commit

        # 2. Asignar todos los permisos (RoleViewLink) por defecto a True
        all_views = session.exec(select(View).where(View.deleted == False)).all()
        links_to_add = []
        current_time = datetime.utcnow()
        for view in all_views:
            links_to_add.append(
                RoleViewLink(
                    id_role=role_db.id,
                    id_view=view.id,
                    enabled=True, # Por defecto, habilitado
                    created_at=current_time,
                    updated_at=current_time
                )
            )
        
        session.add_all(links_to_add)
        session.commit()
        session.refresh(role_db)
        
        return role_db

    except HTTPException as http_exc:
        session.rollback()
        raise http_exc
    except Exception as e:
        session.rollback() 
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al crear el rol: {str(e)}")

# ----------------------------------------------------------------------
# ENDPOINT 3: ACTUALIZAR ROL (PATCH /roles/{role_id})
# ----------------------------------------------------------------------

@router.patch("/{role_id}", response_model=RoleRead, summary="Actualiza nombre y/o estado de un rol")
def update_role(role_id: int, role_data: RoleUpdate, session: SessionDep):
    """Actualiza campos del rol, manteniendo la unicidad del nombre."""
    try:
        role_db = session.get(Role, role_id)

        if not role_db or role_db.deleted is True:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado o eliminado.")
        
        data_to_update = role_data.model_dump(exclude_unset=True)
        
        # Validación de unicidad si se intenta cambiar el nombre
        if "name" in data_to_update and data_to_update["name"] != role_db.name:
            existing_role = session.exec(
                select(Role).where(Role.name == data_to_update["name"], Role.deleted == False)
            ).first()
            
            if existing_role and existing_role.id != role_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ya existe un rol activo con el nombre: '{data_to_update['name']}'." )

        role_db.sqlmodel_update(data_to_update)
        role_db.updated_at = datetime.utcnow()
        
        session.add(role_db)
        session.commit()
        session.refresh(role_db)
        return role_db
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al actualizar el rol: {str(e)}")

# ----------------------------------------------------------------------
# ENDPOINT 4: ELIMINAR ROL (DELETE /roles/{role_id}) - SOFT DELETE
# ----------------------------------------------------------------------

@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Realiza la eliminación suave de un rol")
def soft_delete_role(role_id: int, session: SessionDep):
    """Realiza la 'Eliminación Suave' de un rol, marcando 'deleted=True' y 'deleted_on'."""
    try:
        role_db = session.get(Role, role_id)

        if not role_db:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado.")
        
        if role_db.deleted is True:
            return Response(status_code=status.HTTP_204_NO_CONTENT)

        current_time = datetime.utcnow()

        # Aplicar Soft Delete
        role_db.deleted = True
        role_db.deleted_on = current_time
        role_db.updated_at = current_time
        session.add(role_db)
        session.commit()
        
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al eliminar el rol: {str(e)}")

# ----------------------------------------------------------------------
# ENDPOINT 5: ACTUALIZAR PERMISOS POR ROL (PATCH /roles/{role_id}/permissions)
# ----------------------------------------------------------------------

@router.patch("/{role_id}/permissions", response_model=List[RoleViewUpdateStatus], summary="Actualiza el estado de los permisos (habilitado/deshabilitado) para un rol específico")
def update_role_permissions(
    role_id: int, 
    permission_updates: List[RoleViewUpdateStatus], 
    session: SessionDep
):
    """
    Actualiza el estado 'enabled' (True/False) de los enlaces RoleViewLink de un rol 
    para una lista de vistas específicas (maneja los checkboxes).
    """
    try:
        role_db = session.get(Role, role_id)
        if not role_db or role_db.deleted is True:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado o eliminado.")

        updated_permissions = []
        current_time = datetime.utcnow()
        
        for update_data in permission_updates:
            # 1. Buscar el enlace RoleViewLink específico para Rol y Vista
            link_db = session.exec(
                select(RoleViewLink).where(
                    RoleViewLink.id_role == role_id,
                    RoleViewLink.id_view == update_data.id_view
                )
            ).first()

            if link_db:
                # 2. Actualizar el estado 'enabled' si ha cambiado
                if link_db.enabled != update_data.enabled:
                    link_db.enabled = update_data.enabled
                    link_db.updated_at = current_time
                    session.add(link_db)
                    
                updated_permissions.append(update_data)
            else:
                # El enlace debe existir previamente (creado en POST /roles)
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, 
                    detail=f"Enlace de permiso para Vista ID {update_data.id_view} no encontrado para Rol ID {role_id}. Este enlace debe existir previamente."
                )

        session.commit()
        return updated_permissions

    except HTTPException as http_exc:
        session.rollback()
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al actualizar permisos: {str(e)}")
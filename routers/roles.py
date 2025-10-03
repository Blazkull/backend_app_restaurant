from fastapi import APIRouter, Depends, status, HTTPException
from sqlmodel import select
from datetime import datetime
from typing import List
from starlette.responses import Response
import os
# Importa dependencias y modelos
from core.database import SessionDep
# Importación clave para la AUTORIZACIÓN
from core.security import check_permission 
from models.roles import Role 
from models.views import View
from models.link_models import RoleViewLink 
from schemas.roles_schema import RoleCreate, RoleRead, RoleUpdate
from schemas.role_view_link_schema import RoleViewUpdateStatus


ADMIN_ROLES_PATH: str = os.getenv("ADMIN_ROLES_PATH")


# El router no lleva dependencias globales; estas se aplican a nivel de endpoint
# para permitir un control de permisos granular.
router = APIRouter(
    prefix="/api/roles", 
    tags=["ROLES"]
) 

# ---
## 1. Listar Roles Activos (GET /roles)

@router.get(
    "", 
    response_model=List[RoleRead], 
    summary="Listar roles activos",
    # 🚨 Permiso requerido: /api/roles (para leer la lista)
    dependencies=[Depends(check_permission(ADMIN_ROLES_PATH))] 
)
def list_roles(session: SessionDep):
    """Obtiene una lista de todos los roles activos (deleted=False)."""
    try:
        statement = select(Role).where(Role.deleted == False)
        return session.exec(statement).all()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al listar roles: {str(e)}")

# ---
## 2. Crear Rol (POST /roles)

@router.post(
    "", 
    response_model=RoleRead, 
    status_code=status.HTTP_201_CREATED, 
    summary="Crear nuevo rol y asignarle permisos por defecto",
    # 🚨 Permiso requerido: /api/roles (para crear un nuevo rol)
    dependencies=[Depends(check_permission(ADMIN_ROLES_PATH))] 
)
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

# ---
## 3. Actualizar Rol (PATCH /roles/{role_id})

@router.patch(
    "/{role_id}", 
    response_model=RoleRead, 
    summary="Actualiza nombre y/o estado de un rol",
    # 🚨 Permiso requerido: /api/roles (para editar un rol)
    dependencies=[Depends(check_permission(ADMIN_ROLES_PATH))] 
)
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

# ---
## 4. Eliminar Rol (DELETE /roles/{role_id}) - Soft Delete

@router.delete(
    "/{role_id}", 
    status_code=status.HTTP_204_NO_CONTENT, 
    summary="Realiza la eliminación suave de un rol",
    # 🚨 Permiso requerido: /api/roles (para eliminar un rol)
    dependencies=[Depends(check_permission(ADMIN_ROLES_PATH))] 
)
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

# ---
## 5. Actualizar Permisos por Rol (PATCH /roles/{role_id}/permissions)

@router.patch(
    "/{role_id}/permissions", 
    response_model=List[RoleViewUpdateStatus], 
    summary="Actualiza el estado de los permisos (habilitado/deshabilitado) para un rol específico",
    # 🚨 Permiso requerido: /api/roles (para modificar los permisos)
    dependencies=[Depends(check_permission("/api/roles"))]
)
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
    
# ---
## 6. Obtener Permisos de un Rol Específico (GET /roles/{role_id}/permissions)

@router.get(
    "/{role_id}/permissions", 
    response_model=List[RoleViewUpdateStatus], # Reutilizamos este schema para la lectura
    summary="Obtiene la lista de vistas y su estado de permiso para un rol",
    # 🚨 Permiso requerido: /api/roles (para ver los permisos del rol)
    dependencies=[Depends(check_permission(ADMIN_ROLES_PATH))] 
)
def get_role_permissions(
    role_id: int, 
    session: SessionDep
):
    """
    Recupera todos los enlaces RoleViewLink (permisos) de un rol. 
    Esto incluye todas las vistas que el rol puede tener, junto con su estado 'enabled'.
    """
    try:
        # 1. Verificar la existencia del rol
        role_db = session.get(Role, role_id)
        if not role_db or role_db.deleted is True:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado o eliminado.")

        # 2. Obtener todos los enlaces RoleViewLink para el rol
        statement = select(RoleViewLink).where(RoleViewLink.id_role == role_id)
        permissions_links = session.exec(statement).all()
        
        if not permissions_links:
             # Si no hay enlaces, significa que el rol no tiene vistas asignadas (quizás Views está vacío)
             return []
        
        return permissions_links

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        # Esto atrapará cualquier error de DB o de carga de relaciones
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al obtener permisos: {str(e)}")
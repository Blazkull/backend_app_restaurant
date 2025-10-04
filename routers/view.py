from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlmodel import select
from starlette.responses import Response
import os

# Importaciones de Core
from core.database import SessionDep
from core.security import decode_token

# Importaciones de Modelos y Schemas
from models.views import View 
from models.status import Status 
from schemas.views_schema import ViewRead, ViewCreate, ViewUpdate 

# Configuración del router
router = APIRouter(prefix="/api/views", tags=["VIEWS"]) 

# ----------------------------------------------------------------------
# ENDPOINT 1: LISTAR Y FILTRAR VISTAS (GET /views/) -> SOLO ACTIVAS
# ----------------------------------------------------------------------

@router.get(
    "/", 
    response_model=List[ViewRead], 
    summary="Listar y filtrar vistas activas con paginación",
    # 1: Permiso para ver la lista de vistas
    dependencies=[Depends(decode_token)]
)
def read_views(
    session: SessionDep,
    
    # Paginación
    offset: int = Query(default=0, ge=0, description="Número de registros a omitir (offset)."),
    limit: int = Query(default=10, le=100, description="Máxima cantidad de vistas a retornar (limit)."),
    
    # Filtrado por Estado
    status_id: Optional[int] = Query(default=None, description="Filtrar por ID de estado."),
    status_name: Optional[str] = Query(default=None, description="Filtrar por nombre del estado."),
    
    # Búsqueda por Nombre de Vista (parcial)
    name_search: Optional[str] = Query(default=None, description="Buscar por nombre de la vista (parcialmente)."),
    
    # current_user ya no es necesario aquí, lo maneja check_permission
) -> List[ViewRead]:
    """
    Lista vistas permitiendo filtros y paginación, **excluyendo a las vistas con deleted=True por defecto**.
    """
    
    query = select(View)
    
    # --- EXCLUSIÓN CLAVE: Excluir vistas eliminadas (deleted=False) ---
    query = query.where(View.deleted == False)
    # -------------------------------------------------------------------
    
    # Filtrar por ID de estado
    if status_id is not None:
        query = query.where(View.id_status == status_id)
        
    # Filtrar por Nombre del estado
    if status_name:
        # Usa .join() para relacionar View y Status
        query = query.join(Status, View.id_status == Status.id).where(Status.name.ilike(f"%{status_name}%"))
        
    # Filtrar por nombre de vista
    if name_search:
        query = query.where(View.name.ilike(f"%{name_search}%"))
        
    # Aplicar Paginación
    query = query.offset(offset).limit(limit)
    
    views = session.exec(query).all()
    
    if not views and (offset > 0 or status_id or status_name or name_search):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontraron vistas que coincidan con los criterios de búsqueda o paginación."
        )

    return views


# ----------------------------------------------------------------------
# ENDPOINT 2: LISTAR VISTAS ELIMINADAS (GET /views/deleted)
# ----------------------------------------------------------------------

@router.get(
    "/deleted", 
    response_model=List[ViewRead], 
    summary="Listar vistas marcadas como eliminadas (deleted=True) con paginación",
    # 2: Permiso para ver la papelera de reciclaje
    dependencies=[Depends(decode_token)]
)
def read_deleted_views(
    session: SessionDep,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=10, le=100)
) -> List[ViewRead]:
    """
    Lista solo las vistas cuyo campo 'deleted' es True.
    """
    query = select(View).where(View.deleted == True).offset(offset).limit(limit)
    views = session.exec(query).all()
    
    if not views and offset > 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontraron vistas eliminadas en el rango de paginación."
        )
    
    return views


# ----------------------------------------------------------------------
# ENDPOINT 3: OBTENER VISTA POR ID (GET /views/{view_id}) -> SOLO ACTIVAS
# ----------------------------------------------------------------------

@router.get(
    "/{view_id}", 
    response_model=ViewRead, 
    summary="Obtener una vista por ID (excluye eliminadas)",
    # 3: Permiso para ver una vista individual
    dependencies=[Depends(decode_token)]
)
def read_view(view_id: int, session: SessionDep):
    """
    Busca una vista por su ID. Retorna 404 si no existe O si está marcada como eliminada.
    """
    try:
        query = select(View).where(
            View.id == view_id, 
            View.deleted == False 
        )
        view_db = session.exec(query).first()
        
        if not view_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Vista no existe o está eliminada."
            )
            
        return view_db 
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving view: {str(e)}",
        )

# ----------------------------------------------------------------------
# ENDPOINT 4: CREAR VISTA (POST /views/)
# ----------------------------------------------------------------------

@router.post(
    "/", 
    response_model=ViewRead, 
    status_code=status.HTTP_201_CREATED, 
    summary="Crear una nueva vista/recurso.",
    # 4: Permiso para crear vistas
    dependencies=[Depends(decode_token)]
)
def create_view(view_data: ViewCreate, session: SessionDep):
    """
    Crea una nueva entrada de Vista, validando la unicidad del nombre y el path entre las vistas activas.
    """
    try:
        # Validación: Unicidad del Nombre y Path (solo entre vistas que no están eliminadas)
        existing_name = session.exec(
            select(View).where(View.name == view_data.name, View.deleted == False)
        ).first()
        existing_path = session.exec(
            select(View).where(View.path == view_data.path, View.deleted == False) # ⬅️ Asume que View.path existe
        ).first()
        
        if existing_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Ya existe una vista activa con el nombre: '{view_data.name}'." 
            )
        if existing_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Ya existe una vista activa con el path (ruta): '{view_data.path}'." 
            )

        # Creación del Objeto
        view_db = View.model_validate(view_data.model_dump())
        
        current_time = datetime.utcnow()
        view_db.created_at = current_time
        view_db.updated_at = current_time

        session.add(view_db)
        session.commit()
        session.refresh(view_db)
        
        # NOTA: En un sistema completo, al crear una vista,
        # deberías crear un RoleViewLink con enabled=False para *todos* los roles existentes,
        # para que el administrador pueda habilitar el permiso después.
        
        return view_db

    except HTTPException as http_exc:
        session.rollback()
        raise http_exc
    except Exception as e:
        session.rollback() 
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear la vista: {str(e)}",
        )

# ----------------------------------------------------------------------
# ENDPOINT 5: ACTUALIZAR VISTA (PATCH /views/{view_id})
# ----------------------------------------------------------------------

@router.patch(
    "/{view_id}", 
    response_model=ViewRead, 
    summary="Actualiza nombre y/o estado de una vista",
    # 5: Permiso para actualizar vistas
    dependencies=[Depends(decode_token)]
)
def update_view(view_id: int, view_data: ViewUpdate, session: SessionDep):
    """Actualiza campos de la vista, manteniendo la unicidad del nombre y path entre las activas."""
    try:
        view_db = session.get(View, view_id)

        if not view_db or view_db.deleted is True:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vista no encontrada o eliminada.")
        
        data_to_update = view_data.model_dump(exclude_unset=True)
        
        # Validación de unicidad si se intenta cambiar el nombre
        if "name" in data_to_update and data_to_update["name"] != view_db.name:
            existing_view = session.exec(
                select(View).where(View.name == data_to_update["name"], View.deleted == False)
            ).first()
            
            if existing_view and existing_view.id != view_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ya existe una vista activa con el nombre: '{data_to_update['name']}'." )
                
        # Validación de unicidad si se intenta cambiar el path
        if "path" in data_to_update and data_to_update["path"] != view_db.path:
            existing_path = session.exec(
                select(View).where(View.path == data_to_update["path"], View.deleted == False)
            ).first()
            
            if existing_path and existing_path.id != view_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ya existe una vista activa con el path: '{data_to_update['path']}'." )

        
        # Lógica de protección contra cambios en 'deleted'
        if "deleted" in data_to_update:
            if data_to_update["deleted"] == False and view_db.deleted == True:
                 raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Restauración debe hacerse usando el endpoint /restore.")
            if data_to_update["deleted"] == True and view_db.deleted == False:
                 raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Eliminación suave debe hacerse usando el endpoint DELETE.")
            del data_to_update["deleted"] 
        
        # Aplicar actualización
        view_db.sqlmodel_update(data_to_update)
        view_db.updated_at = datetime.utcnow()
        
        session.add(view_db)
        session.commit()
        session.refresh(view_db)
        return view_db
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al actualizar la vista: {str(e)}")

# ----------------------------------------------------------------------
# ENDPOINT 6: ELIMINAR VISTA (DELETE /views/{view_id}) - SOFT DELETE
# ----------------------------------------------------------------------

@router.delete(
    "/{view_id}", 
    status_code=status.HTTP_200_OK, 
    response_model=dict,
    summary="Realiza la eliminación suave de una vista",
    # 6: Permiso para eliminar vistas (soft delete)
    dependencies=[Depends(decode_token)]
)
def soft_delete_view(view_id: int, session: SessionDep):
    """Realiza la 'Eliminación Suave' de una vista, marcando 'deleted=True'."""
    try:
        view_db = session.get(View, view_id)

        if not view_db:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vista no encontrada.")
        
        if view_db.deleted is True:
            return Response(status_code=status.HTTP_204_NO_CONTENT)

        current_time = datetime.utcnow()

        # Aplicar Soft Delete
        view_db.deleted = True
        view_db.deleted_on = current_time
        view_db.updated_at = current_time
        session.add(view_db)
        
        session.commit()
        
        return {"message": f"La vista {view_db.name} ha sido eliminada exitosamente el {current_time.isoformat()}."}
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al eliminar la vista: {str(e)}")

# ----------------------------------------------------------------------
# ENDPOINT 7: RESTAURAR VISTA (PATCH /views/{view_id}/restore)
# ----------------------------------------------------------------------

@router.patch(
    "/{view_id}/restore", 
    response_model=ViewRead, 
    summary="Restaura una vista previamente eliminada",
    # 7: Permiso para restaurar vistas
    dependencies=[Depends(decode_token)]
)
def restore_deleted_view(view_id: int, session: SessionDep):
    """
    Restaura una vista previamente eliminada (Soft Delete), 
    cambiando 'deleted' a False y limpiando 'deleted_on'.
    """
    try:
        view_db = session.get(View, view_id)

        if not view_db:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vista no encontrada.")
        
        # Solo permite la restauración si está actualmente eliminado
        if view_db.deleted is False:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La vista no está eliminada y no se puede restaurar.")

        current_time = datetime.utcnow()

        # Restaurar la vista
        view_db.deleted = False
        view_db.deleted_on = None  
        view_db.updated_at = current_time 

        session.add(view_db)
        session.commit()
        session.refresh(view_db)

        return view_db
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al restaurar la vista: {str(e)}",)
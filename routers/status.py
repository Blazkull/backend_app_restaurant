from fastapi import APIRouter, Depends, status, HTTPException
from sqlmodel import select
from datetime import datetime
from typing import List

# Importa las dependencias del Core
from core.database import SessionDep
from core.security import decode_token 

from models.status import Status # Asume que ahora tiene 'deleted' y 'deleted_on'
from schemas.status_schema import StatusCreate, StatusRead, StatusUpdate 

# Configuración del Router
router = APIRouter(
    prefix="/api/status", 
    tags=["STATUS"], 
    dependencies=[Depends(decode_token)]
) 


# --- RUTAS DE LECTURA (GET) ---

@router.get("", response_model=List[StatusRead]) # Ruta: /api/status
def list_status(session: SessionDep):
    """
    Obtiene una lista de todos los estados **activos** (deleted=False).
    """
    try:
        # >>> CAMBIO 1: Filtra por 'deleted == False'
        statement = select(Status).where(Status.deleted == False)
        return session.exec(statement).all()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar los estados: {str(e)}",
        )

@router.get("/{status_id}", response_model=StatusRead) # Ruta: /api/status/{status_id}
def read_status(status_id: int, session: SessionDep):
    """Obtiene un estado específico por su ID. Solo devuelve estados activos."""
    try:
        status_db = session.get(Status, status_id)
        
        # >>> CAMBIO 2: Validación con 'deleted is True'
        if not status_db or status_db.deleted is True:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Estado no encontrado o eliminado."
            )
        return status_db
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al leer el estado: {str(e)}",
        )

# --- RUTA PARA CREACIÓN (POST) ---

@router.post("", response_model=StatusRead, status_code=status.HTTP_201_CREATED, summary="Crea un nuevo estado, validando que el nombre sea único entre los activos.") # Ruta: /api/status
def create_status(status_data: StatusCreate, session: SessionDep):

    try:
        # Validación de Unicidad por nombre (solo para registros activos)
        existing_status = session.exec(
            select(Status)
            .where(Status.name == status_data.name)
            .where(Status.deleted == False)
        ).first()
        if existing_status:
            raise HTTPException(
               status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ya existe un estado activo con el nombre: '{status_data.name}'." 
            )

        # Creación del Estado
        status_db = Status.model_validate(status_data.model_dump())
        status_db.created_at = datetime.utcnow()
        status_db.updated_at = datetime.utcnow()
        # 'deleted' y 'deleted_on' se establecen por defecto (False y None)

        session.add(status_db)
        session.commit()
        session.refresh(status_db)
        
        return status_db

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback() 
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear el estado: {str(e)}",
        )

# --- RUTA PARA ACTUALIZACIÓN (PATCH) ---

@router.patch("/{status_id}", response_model=StatusRead) # Ruta: /api/status/{status_id}
def update_status(status_id: int, status_data: StatusUpdate, session: SessionDep):
    """Actualiza el nombre y/o descripción del estado, manteniendo la unicidad."""
    try:
        status_db = session.get(Status, status_id)

        # >>> CAMBIO 4: Validación con 'deleted is True'
        if not status_db or status_db.deleted is True:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Estado no encontrado o eliminado."
            )
        
        data_to_update = status_data.model_dump(exclude_unset=True)
        
        # Validación de unicidad si se intenta cambiar el nombre
        if "name" in data_to_update and data_to_update["name"] != status_db.name:
            # >>> CAMBIO 5: Filtra por 'deleted == False'
            existing_status = session.exec(
                select(Status)
                .where(Status.name == data_to_update["name"])
                .where(Status.deleted == False)
            ).first()
            
            if existing_status and existing_status.id != status_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ya existe un estado activo con el nombre: '{data_to_update['name']}'."
                )

        # Aplicar actualización y actualizar timestamp
        status_db.sqlmodel_update(data_to_update)
        status_db.updated_at = datetime.utcnow()
        
        session.add(status_db)
        session.commit()
        session.refresh(status_db)
        return status_db
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar el estado: {str(e)}",
        )

# --- RUTA PARA ELIMINACIÓN SUAVE (DELETE) ---

@router.delete("/{status_id}", status_code=status.HTTP_200_OK, response_model=dict) # Ruta: /api/status/{status_id}
def soft_delete_status(status_id: int, session: SessionDep):
    """Realiza la 'Eliminación Suave' de un estado, marcando 'deleted=True'."""
    try:
        status_db = session.get(Status, status_id)

        if not status_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Estado no encontrado."
            )
        
        # >>> CAMBIO 6: Usar 'deleted is True'
        if status_db.deleted is True:
            return {"message": f"El Estado (ID: {status_id}) ya estaba marcado como eliminado."}

        # NOTA: En un entorno de producción, aquí se debería validar si este
        # estado está siendo referenciado por órdenes u otras entidades
        # para evitar inconsistencias.

        current_time = datetime.utcnow()

        # Aplicar Soft Delete
        # >>> CAMBIO 7: Asignar deleted=True y deleted_on
        status_db.deleted = True
        status_db.deleted_on = current_time
        status_db.updated_at = current_time
        session.add(status_db)
        session.commit()
        
        return {"message": f"Estado {status_db.name} (ID: {status_id}) ha sido eliminado  exitosamente el {current_time.isoformat()}."}
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar el estado: {str(e)}",
        )

# --- RUTA PARA RESTAURACIÓN (PATCH /restore) ---

@router.patch("/{status_id}/restore", response_model=StatusRead) # Ruta: /api/status/{status_id}/restore
def restore_deleted_status(status_id: int, session: SessionDep):
    """
    Restaura un estado previamente eliminado (Soft Delete), 
    cambiando 'deleted' a False y limpiando 'deleted_on'.
    """
    try:
        status_db = session.get(Status, status_id)

        if not status_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Estado no encontrado."
            )
        
        # Solo permite la restauración si está actualmente eliminado
        if status_db.deleted is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="El estado no está eliminado y no puede ser restaurado."
            )

        # Validación de unicidad: Verificar si el nombre está ocupado por otro estado activo
        existing_status = session.exec(
            select(Status)
            .where(Status.name == status_db.name)
            .where(Status.deleted == False)
        ).first()

        if existing_status:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail=f"Conflicto: No se puede restaurar. El nombre '{status_db.name}' ya está en uso por otro estado activo (ID: {existing_status.id})."
            )

        current_time = datetime.utcnow()

        # Restaurar el estado
        status_db.deleted = False
        status_db.deleted_on = None  # Limpia la marca de tiempo de eliminación
        status_db.updated_at = current_time 

        session.add(status_db)
        session.commit()
        session.refresh(status_db)

        return status_db
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al restaurar el estado: {str(e)}",
        )
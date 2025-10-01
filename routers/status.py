from fastapi import APIRouter, Depends, status, HTTPException
from sqlmodel import select
from datetime import datetime
from typing import List

# Importa las dependencias del Core
from core.database import SessionDep
from core.security import decode_token 

from models.status import Status
from schemas.status_schema import StatusCreate, StatusRead, StatusUpdate 

# Configuración del Router
# Uso 'STATUS' como tag para agrupar en la documentación de la API (Swagger/Redoc)
router = APIRouter(tags=["STATUS"]) 


# Rutas para lectura (GET)
@router.get("/api/status", response_model=List[StatusRead], dependencies=[Depends(decode_token)])
def list_status(session: SessionDep):
    """
    Obtiene una lista de todos los estados **activos** (no eliminados).
    """
    try:
        # Filtra por estados donde deleted_at es NULL (no eliminados)
        statement = select(Status).where(Status.deleted_at == None)
        return session.exec(statement).all()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar los estados: {str(e)}",
        )

@router.get("/api/status/{status_id}", response_model=StatusRead, dependencies=[Depends(decode_token)])
def read_status(status_id: int, session: SessionDep):
    """Obtiene un estado específico por su ID."""
    try:
        status_db = session.get(Status, status_id)
        
        # Validación de existencia y de eliminación suave
        if not status_db or status_db.deleted_at is not None:
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

# Ruta para creacion (CREATE)
@router.post("/api/status", response_model=StatusRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(decode_token)])
def create_status(status_data: StatusCreate, session: SessionDep):
    """Crea un nuevo estado, validando que el nombre sea único."""
    try:
        # Validación de Unicidad por nombre (solo para registros activos)
        existing_status = session.exec(
            select(Status)
            .where(Status.name == status_data.name)
            .where(Status.deleted_at == None)
        ).first()
        if existing_status:
            raise HTTPException(
               status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ya existe un estado activo con el nombre: '{status_data.name}'." 
            )

        # Creación del Estado
        status_db = Status.model_validate(status_data.model_dump())
        status_db.created_at = datetime.utcnow()
        status_db.updated_at = datetime.utcnow()

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

# Rutas para actualizar (PATCH)
@router.patch("/api/status/{status_id}", response_model=StatusRead, dependencies=[Depends(decode_token)])
def update_status(status_id: int, status_data: StatusUpdate, session: SessionDep):
    """Actualiza campos del estado, manteniendo la unicidad del nombre."""
    try:
        status_db = session.get(Status, status_id)

        # Validación: El estado debe existir y no estar eliminado
        if not status_db or status_db.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Estado no encontrado o eliminado."
            )
        
        data_to_update = status_data.model_dump(exclude_unset=True)
        
        # Validación de unicidad si se intenta cambiar el nombre
        if "name" in data_to_update and data_to_update["name"] != status_db.name:
            existing_status = session.exec(
                select(Status)
                .where(Status.name == data_to_update["name"])
                .where(Status.deleted_at == None)
            ).first()
            
            # Si el nombre existe Y no pertenece al estado que estamos actualizando
            if existing_status and existing_status.id != status_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ya existe otro estado activo con el nombre: '{data_to_update['name']}'."
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

# Ruta para eliminacion (DELETE - Soft Delete)
@router.delete("/api/status/{status_id}", status_code=status.HTTP_200_OK, response_model=dict, dependencies=[Depends(decode_token)])
def delete_status(status_id: int, session: SessionDep):
    """Realiza la 'Eliminación Suave' de un estado."""
    try:
        status_db = session.get(Status, status_id)

        if not status_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Estado no encontrado."
            )
        
        if status_db.deleted_at is not None:
            return {"message": f"El Estado (ID: {status_id}) ya estaba marcado como eliminado."}

        current_time = datetime.utcnow()

        # Aplicar Soft Delete
        status_db.deleted_at = current_time
        status_db.updated_at = current_time
        session.add(status_db)
        session.commit()
        
        return {"message": f"Estado (ID: {status_id}) eliminado (Soft Delete) exitosamente."}
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar el estado: {str(e)}",
        )
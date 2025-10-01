from fastapi import APIRouter, Depends, status, HTTPException
from sqlmodel import select
from datetime import datetime
from typing import List

# Importa las dependencias del Core
from core.database import SessionDep
from core.security import decode_token 

from models.type_identification import TypeIdentification # Asume que ahora tiene 'deleted' y 'deleted_on'
from schemas.type_identification_schema import TypeIdentificationCreate, TypeIdentificationRead, TypeIdentificationUpdate 

# Configuración del Router
router = APIRouter(
    prefix="/api/type_identification", 
    tags=["TYPE IDENTIFICATION"], 
    dependencies=[Depends(decode_token)]
) 

# --- RUTAS DE LECTURA (GET) ---

@router.get("", response_model=List[TypeIdentificationRead]) # Ruta: /api/type_identification
def list_type_identifications(session: SessionDep):
    """
    Obtiene una lista de todos los tipos de identificación **activos** (deleted=False).
    """
    try:
        # Filtra por 'deleted == False'
        statement = select(TypeIdentification).where(TypeIdentification.deleted == False)
        return session.exec(statement).all()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar los tipos de identificación: {str(e)}",
        )

@router.get("/{type_id}", response_model=TypeIdentificationRead) # Ruta: /api/type_identification/{type_id}
def read_type_identification(type_id: int, session: SessionDep):
    """Obtiene un tipo de identificación específico por su ID. Solo devuelve activos."""
    try:
        type_db = session.get(TypeIdentification, type_id)
        
        # Validación de existencia y de eliminación suave
        if not type_db or type_db.deleted is True:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de identificación no encontrado o eliminado."
            )
        return type_db
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al leer el tipo de identificación: {str(e)}",
        )

# --- RUTA PARA CREACIÓN (POST) ---

@router.post("", response_model=TypeIdentificationRead, status_code=status.HTTP_201_CREATED) # Ruta: /api/type_identification
def create_type_identification(type_data: TypeIdentificationCreate, session: SessionDep):
    """Crea un nuevo tipo de identificación, validando que el nombre sea único entre los activos."""
    try:
        # Validación de Unicidad por nombre (solo para registros activos)
        existing_type = session.exec(
            select(TypeIdentification)
            .where(TypeIdentification.type_identification == type_data.type_identification)
            .where(TypeIdentification.deleted == False)
        ).first()
        if existing_type:
            raise HTTPException(
               status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ya existe un tipo de identificación activo con el nombre: '{type_data.type_identification}'." 
            )

        # Creación del Tipo de Identificación
        type_db = TypeIdentification.model_validate(type_data.model_dump())
        type_db.created_at = datetime.utcnow()
        type_db.updated_at = datetime.utcnow()

        session.add(type_db)
        session.commit()
        session.refresh(type_db)
        
        return type_db

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback() 
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear el tipo de identificación: {str(e)}",
        )

# --- RUTA PARA ACTUALIZACIÓN (PATCH) ---

@router.patch("/{type_id}", response_model=TypeIdentificationRead) # Ruta: /api/type_identification/{type_id}
def update_type_identification(type_id: int, type_data: TypeIdentificationUpdate, session: SessionDep):
    """Actualiza el tipo de identificación, manteniendo la unicidad."""
    try:
        type_db = session.get(TypeIdentification, type_id)

        # Validación: Debe existir y no estar eliminado
        if not type_db or type_db.deleted is True:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de identificación no encontrado o eliminado."
            )
        
        data_to_update = type_data.model_dump(exclude_unset=True)
        
        # Validación de unicidad si se intenta cambiar el nombre
        new_name = data_to_update.get("type_identification")
        if new_name is not None and new_name != type_db.type_identification:
            existing_type = session.exec(
                select(TypeIdentification)
                .where(TypeIdentification.type_identification == new_name)
                .where(TypeIdentification.deleted == False)
            ).first()
            
            if existing_type and existing_type.id != type_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ya existe un tipo de identificación activo con el nombre: '{new_name}'."
                )

        # Aplicar actualización y actualizar timestamp
        type_db.sqlmodel_update(data_to_update)
        type_db.updated_at = datetime.utcnow()
        
        session.add(type_db)
        session.commit()
        session.refresh(type_db)
        return type_db
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar el tipo de identificación: {str(e)}",
        )

# --- RUTA PARA ELIMINACIÓN SUAVE (DELETE) ---

@router.delete("/{type_id}", status_code=status.HTTP_200_OK, response_model=dict) # Ruta: /api/type_identification/{type_id}
def soft_delete_type_identification(type_id: int, session: SessionDep):
    """Realiza la 'Eliminación Suave' de un tipo de identificación."""
    try:
        type_db = session.get(TypeIdentification, type_id)

        if not type_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de identificación no encontrado."
            )
        
        if type_db.deleted is True:
            return {"message": f"El Tipo de Identificación (ID: {type_id}) ya estaba marcado como eliminado."}

        # NOTA: En un entorno real, se debería validar si este tipo de identificación
        # está siendo referenciado por usuarios u otras entidades.

        current_time = datetime.utcnow()

        # Aplicar Soft Delete
        type_db.deleted = True
        type_db.deleted_on = current_time
        type_db.updated_at = current_time
        session.add(type_db)
        session.commit()
        
        return {"message": f"Tipo de Identificación (ID: {type_id}) eliminado (Soft Delete) exitosamente el {current_time.isoformat()}."}
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar el tipo de identificación: {str(e)}",
        )

# --- RUTA PARA RESTAURACIÓN (PATCH /restore) ---

@router.patch("/{type_id}/restore", response_model=TypeIdentificationRead) # Ruta: /api/type_identification/{type_id}/restore
def restore_deleted_type_identification(type_id: int, session: SessionDep):
    """
    Restaura un tipo de identificación previamente eliminado (Soft Delete), 
    cambiando 'deleted' a False y limpiando 'deleted_on'.
    """
    try:
        type_db = session.get(TypeIdentification, type_id)

        if not type_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Tipo de identificación no encontrado."
            )
        
        # Solo permite la restauración si está actualmente eliminado
        if type_db.deleted is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="El tipo de identificación no está eliminado y no puede ser restaurado."
            )

        # Validación de unicidad: Verificar si el nombre está ocupado por otro tipo activo
        existing_type = session.exec(
            select(TypeIdentification)
            .where(TypeIdentification.type_identification == type_db.type_identification)
            .where(TypeIdentification.deleted == False)
        ).first()

        if existing_type:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail=f"Conflicto: No se puede restaurar. El nombre '{type_db.type_identification}' ya está en uso por otro tipo de identificación activo (ID: {existing_type.id})."
            )

        current_time = datetime.utcnow()

        # Restaurar el tipo
        type_db.deleted = False
        type_db.deleted_on = None  # Limpia la marca de tiempo de eliminación
        type_db.updated_at = current_time 

        session.add(type_db)
        session.commit()
        session.refresh(type_db)

        return type_db
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al restaurar el tipo de identificación: {str(e)}",
        )
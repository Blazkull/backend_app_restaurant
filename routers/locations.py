from fastapi import APIRouter, Depends, status, HTTPException
from sqlmodel import select
from datetime import datetime
from typing import List

# Importa las dependencias del Core (Asegúrate de que estas rutas sean correctas)
from core.database import SessionDep
from core.security import decode_token 

# Importa el modelo y los schemas actualizados
from models.locations import Location 
from schemas.locations_schema import LocationCreate, LocationRead, LocationUpdate 

# Configuración del Router con prefijo y dependencia de autenticación
router = APIRouter(
    prefix="/api/locations", 
    tags=["LOCATIONS"], 
    dependencies=[Depends(decode_token)] # Autenticación global
) 

# --- ENDPOINTS CRUD BÁSICOS ---

# 1. Obtener lista de ubicaciones (GET)
# Ruta: /api/locations
@router.get("", response_model=List[LocationRead])
def list_locations(session: SessionDep):
    """
    Obtiene una lista de todas las ubicaciones **activas** (deleted=False).
    """
    try:
        # Filtra por ubicaciones donde deleted es False
        statement = select(Location).where(Location.deleted == False)
        locations = session.exec(statement).all()
        return locations
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar las ubicaciones: {str(e)}",
        )

# 2. Obtener una ubicación en particular (GET)
# Ruta: /api/locations/{location_id}
@router.get("/{location_id}", response_model=LocationRead)
def read_location(location_id: int, session: SessionDep):
    """Obtiene una ubicación específica por su ID. Solo devuelve ubicaciones activas."""
    try:
        location_db = session.get(Location, location_id)
        
        # Validación de existencia y de eliminación suave (debe existir y no estar eliminada)
        if not location_db or location_db.deleted is True:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Ubicación no encontrada o eliminada."
            )
        return location_db
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al leer la ubicación: {str(e)}",
        )

# 3. Crear una nueva ubicación (POST)
# Ruta: /api/locations
@router.post("", response_model=LocationRead, status_code=status.HTTP_201_CREATED)
def create_location(location_data: LocationCreate, session: SessionDep):
    """Crea una nueva ubicación, validando que el nombre sea único entre las activas."""
    try:
        # Validación de unicidad por nombre (solo para ubicaciones activas)
        existing_location = session.exec(
            select(Location)
            .where(Location.name == location_data.name)
            .where(Location.deleted == False)
        ).first()
        if existing_location:
            raise HTTPException(
               status_code=status.HTTP_400_BAD_REQUEST, 
               detail="Ya existe una ubicación activa con este nombre." 
            )

        # Crear el objeto y asignar timestamps (deleted=False por defecto)
        location_db = Location.model_validate(location_data.model_dump())
        location_db.created_at = datetime.utcnow()
        location_db.updated_at = datetime.utcnow()

        session.add(location_db)
        session.commit()
        session.refresh(location_db)
        return location_db

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback() 
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear la ubicación: {str(e)}",
        )

# 4. Actualizar parcialmente una ubicación (PATCH)
# Ruta: /api/locations/{location_id}
@router.patch("/{location_id}", response_model=LocationRead)
def update_location(location_id: int, location_data: LocationUpdate, session: SessionDep):
    """Actualiza campos de una ubicación, manteniendo la unicidad del nombre si se cambia."""
    try:
        location_db = session.get(Location, location_id)

        # Validación: La ubicación debe existir y no estar eliminada
        if not location_db or location_db.deleted is True:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Ubicación no encontrada o eliminada."
            )
        
        data_to_update = location_data.model_dump(exclude_unset=True)

        # Validación de unicidad si se está actualizando el nombre
        if "name" in data_to_update and data_to_update["name"] != location_db.name:
            existing_location = session.exec(
                select(Location)
                .where(Location.name == data_to_update["name"])
                .where(Location.deleted == False) # Solo verifica duplicados activos
            ).first()
            if existing_location and existing_location.id != location_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="Ya existe otra ubicación activa con este nombre."
                )

        # Aplicar la actualización y el timestamp
        location_db.sqlmodel_update(data_to_update)
        location_db.updated_at = datetime.utcnow()
        
        session.add(location_db)
        session.commit()
        session.refresh(location_db)
        return location_db
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar la ubicación: {str(e)}",
        )

# 5. Eliminación Suave (DELETE)
# Ruta: /api/locations/{location_id}
@router.delete("/{location_id}", status_code=status.HTTP_200_OK, response_model=dict)
def soft_delete_location(location_id: int, session: SessionDep):
    """
    Realiza la 'Eliminación Suave' (Soft Delete) marcando 'deleted=True' y 'deleted_on'.
    """
    try:
        location_db = session.get(Location, location_id)

        # 1. Validación de existencia
        if not location_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Ubicación no encontrada."
            )
        
        # 2. Validación de estado (si ya está eliminada)
        if location_db.deleted is True:
            return {"message": f"La Ubicación {location_db.name} (ID: {location_id}) ya estaba marcada como eliminada."}

        current_time = datetime.utcnow()

        # 3. Aplicar Soft Delete: Actualizar los campos
        location_db.deleted = True
        location_db.deleted_on = current_time # Captura la fecha de eliminación
        location_db.updated_at = current_time # Actualiza el timestamp de modificación

        session.add(location_db)
        session.commit()

        return {"message": f"Ubicación: {location_db.name} (ID: {location_id}) eliminada (Soft Delete) exitosamente el {current_time.isoformat()}."}
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar la ubicación: {str(e)}",
        )

# --- ENDPOINT DE RESTAURACIÓN ---

# 6. Restaurar una ubicación eliminada (PATCH /restore)
# Ruta: /api/locations/{location_id}/restore
@router.patch("/{location_id}/restore", response_model=LocationRead)
def restore_deleted_location(location_id: int, session: SessionDep):
    """
    Restaura una ubicación previamente eliminada (Soft Delete) 
    cambiando 'deleted' a False y limpiando 'deleted_on'.
    """
    try:
        location_db = session.get(Location, location_id)

        if not location_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Ubicación no encontrada."
            )
        
        # Solo permite la restauración si está actualmente eliminada
        if location_db.deleted is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="La ubicación no está eliminada y no puede ser restaurada."
            )

        # Validación de unicidad: Verificar si el nombre está ocupado por otra ubicación activa
        existing_location = session.exec(
            select(Location)
            .where(Location.name == location_db.name)
            .where(Location.deleted == False)
        ).first()

        if existing_location:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail=f"Conflicto: No se puede restaurar. El nombre '{location_db.name}' ya está en uso por otra ubicación activa (ID: {existing_location.id})."
            )

        current_time = datetime.utcnow()

        # Restaurar la ubicación
        location_db.deleted = False
        location_db.deleted_on = None  # Limpia la marca de tiempo de eliminación
        location_db.updated_at = current_time 

        session.add(location_db)
        session.commit()
        session.refresh(location_db)

        return location_db
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al restaurar la ubicación: {str(e)}",
        )
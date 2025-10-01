from fastapi import APIRouter, Depends, status, HTTPException
from sqlmodel import select
from datetime import datetime
from typing import List

# Importa las dependencias del Core
from core.database import SessionDep
from core.security import decode_token 

from models.locations import Location
from schemas.locations_schema import LocationCreate, LocationRead, LocationUpdate 

# Configuración del Router
# Uso 'LOCATIONS' como tag para agrupar en la documentación de la API (Swagger/Redoc)
router = APIRouter(tags=["LOCATIONS"]) 


# Rutas para lectura (GET)
@router.get("/api/locations", response_model=List[LocationRead], dependencies=[Depends(decode_token)])
def list_locations(session: SessionDep):
    """
    Obtiene una lista de todas las ubicaciones **activas** (no eliminadas).
    """
    try:
        # Filtra por ubicaciones donde deleted_at es NULL (no eliminadas)
        statement = select(Location).where(Location.deleted_at == None)
        return session.exec(statement).all()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar las ubicaciones: {str(e)}",
        )

@router.get("/api/locations/{location_id}", response_model=LocationRead, dependencies=[Depends(decode_token)])
def read_location(location_id: int, session: SessionDep):
    """Obtiene una ubicación específica por su ID."""
    try:
        location_db = session.get(Location, location_id)
        
        # Validación de existencia y de eliminación suave
        if not location_db or location_db.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Ubicación no encontrada o eliminada."
            )
        return location_db
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al leer la ubicación: {str(e)}",
        )

# Ruta para creacion (CREATE)
@router.post("/api/locations", response_model=LocationRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(decode_token)])
def create_location(location_data: LocationCreate, session: SessionDep):
    """Crea una nueva ubicación, validando que el nombre sea único."""
    try:
        # Validación de Unicidad por nombre (solo para registros activos)
        existing_location = session.exec(
            select(Location)
            .where(Location.name == location_data.name)
            .where(Location.deleted_at == None)
        ).first()
        if existing_location:
            raise HTTPException(
               status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ya existe una ubicación activa con el nombre: '{location_data.name}'." 
            )

        # Creación de la Ubicación
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

# Rutas para actualizar (PATCH)
@router.patch("/api/locations/{location_id}", response_model=LocationRead, dependencies=[Depends(decode_token)])
def update_location(location_id: int, location_data: LocationUpdate, session: SessionDep):
    """Actualiza campos de la ubicación, manteniendo la unicidad del nombre."""
    try:
        location_db = session.get(Location, location_id)

        # Validación: La ubicación debe existir y no estar eliminada
        if not location_db or location_db.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Ubicación no encontrada o eliminada."
            )
        
        data_to_update = location_data.model_dump(exclude_unset=True)
        
        # Validación de unicidad si se intenta cambiar el nombre
        if "name" in data_to_update and data_to_update["name"] != location_db.name:
            existing_location = session.exec(
                select(Location)
                .where(Location.name == data_to_update["name"])
                .where(Location.deleted_at == None)
            ).first()
            
            # Si el nombre existe Y no pertenece a la ubicación que estamos actualizando
            if existing_location and existing_location.id != location_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ya existe otra ubicación activa con el nombre: '{data_to_update['name']}'."
                )

        # Aplicar actualización y actualizar timestamp
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

# Ruta para eliminacion (DELETE - Soft Delete)
@router.delete("/api/locations/{location_id}", status_code=status.HTTP_200_OK, response_model=dict, dependencies=[Depends(decode_token)])
def delete_location(location_id: int, session: SessionDep):
    """Realiza la 'Eliminación Suave' de una ubicación."""
    try:
        location_db = session.get(Location, location_id)

        if not location_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Ubicación no encontrada."
            )
        
        if location_db.deleted_at is not None:
            return {"message": f"La Ubicación (ID: {location_id}) ya estaba marcada como eliminada."}

        current_time = datetime.utcnow()

        # Aplicar Soft Delete
        location_db.deleted_at = current_time
        location_db.updated_at = current_time
        session.add(location_db)
        session.commit()
        
        return {"message": f"Ubicación (ID: {location_id}) eliminada (Soft Delete) exitosamente."}
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar la ubicación: {str(e)}",
        )
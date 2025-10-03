from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlmodel import select
from sqlalchemy.orm import selectinload
from datetime import datetime
from typing import List, Optional
from starlette.responses import Response

# Importa las dependencias del Core
from core.database import SessionDep
from core.security import decode_token 

from models.tables import Table # Asume que ahora tiene 'deleted' y 'deleted_on'
from schemas.tables_schema import TableCreate, TableRead, TableUpdate 

# Configuración del Router
router = APIRouter(prefix="/api/tables", tags=["TABLES"], dependencies=[Depends(decode_token)]) 


# ----------------------------------------------------------------------
# ENDPOINT 1: LISTAR Y FILTRAR MESAS ACTIVAS (GET /tables)
# ----------------------------------------------------------------------
@router.get("", response_model=List[TableRead], summary="Listar y filtrar mesas activas con paginación")
def list_tables(
    session: SessionDep,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=10, le=100),
    name_search: Optional[str] = Query(default=None, description="Buscar por nombre/número de mesa (parcialmente).")
):
    """
    Obtiene una lista de todas las mesas **activas** (deleted=False).
    """
    try:
        # >>> CAMBIO 1: Filtra por 'deleted == False'
        query = select(Table).where(Table.deleted == False)
        
        # Filtrar por nombre
        if name_search:
            query = query.where(Table.name.ilike(f"%{name_search}%"))
            
        # Aplicar Paginación
        query = query.offset(offset).limit(limit)

        tables = session.exec(query).all()
        
        if not tables and offset > 0:
             raise HTTPException(
                 status_code=status.HTTP_404_NOT_FOUND,
                 detail="No se encontraron más mesas activas en el rango de paginación."
             )
            
        return tables
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar las mesas: {str(e)}",
        )

# ----------------------------------------------------------------------
# ENDPOINT 2: LISTAR MESAS ELIMINADAS (GET /tables/deleted)
# ----------------------------------------------------------------------
@router.get("/deleted", response_model=List[TableRead], summary="Listar mesas marcadas como eliminadas")
def read_deleted_tables(
    session: SessionDep,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=10, le=100)
) -> List[TableRead]:
    """
    Lista solo las mesas cuyo campo 'deleted' es True.
    """
    # >>> CAMBIO 2: Filtra por 'deleted == True'
    query = select(Table).where(Table.deleted == True).offset(offset).limit(limit)
    tables = session.exec(query).all()
    
    if not tables and offset > 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontraron mesas eliminadas en el rango de paginación."
        )
    
    return tables


# ----------------------------------------------------------------------
# ENDPOINT 3: OBTENER MESA POR ID (GET /tables/{table_id})
# ----------------------------------------------------------------------
@router.get("/{table_id}", response_model=TableRead, summary="Obtener una mesa por ID (excluye eliminadas)")
def read_table(table_id: int, session: SessionDep):
    """Obtiene una mesa específica por su ID, excluyendo las eliminadas."""
    try:
        # Usamos select y where para incluir la condición deleted=False
        # >>> CAMBIO 3: Condición 'Table.deleted == False'
        statement = select(Table).where(Table.id == table_id, Table.deleted == False)
        table_db = session.exec(statement).first()
        
        if not table_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Mesa no encontrada o eliminada."
            )
        return table_db
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al leer la mesa: {str(e)}",
        )

# ----------------------------------------------------------------------
# ENDPOINT 4: CREAR MESA (POST /tables)
# ----------------------------------------------------------------------
@router.post("", response_model=TableRead, status_code=status.HTTP_201_CREATED, summary="Crea una nueva mesa")
def create_table(table_data: TableCreate, session: SessionDep):
    """Crea una nueva mesa, validando que el nombre sea único entre las activas."""
    try:
        # Validación de Unicidad por nombre (solo para registros activos)
        # >>> CAMBIO 4: Filtra por 'deleted == False'
        existing_table = session.exec(
            select(Table)
            .where(Table.name == table_data.name)
            .where(Table.deleted == False)
        ).first()
        # Validación de capacidad (si se proporciona)
        if capacity_table_max := 20:
            if table_data.capacity > capacity_table_max or table_data.capacity <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail=f"La capacidad de la mesa debe ser un número positivo y no mayor a {capacity_table_max}."
                )
            
        if existing_table:
            raise HTTPException(
               status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ya existe una mesa activa con el nombre/número: '{table_data.name}'." 
            )

        # Creación de la Mesa
        table_db = Table.model_validate(table_data.model_dump())
        table_db.created_at = datetime.utcnow()
        table_db.updated_at = datetime.utcnow()
        # 'deleted' y 'deleted_on' se establecen por defecto (False y None)

        session.add(table_db)
        session.commit()
        session.refresh(table_db)
        
        return table_db

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback() 
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear la mesa: {str(e)}",
        )

# ----------------------------------------------------------------------
# ENDPOINT 5: ACTUALIZAR MESA (PATCH /tables/{table_id})
# ----------------------------------------------------------------------
@router.patch("/{table_id}", response_model=TableRead, summary="Actualiza campos de la mesa")
def update_table(table_id: int, table_data: TableUpdate, session: SessionDep):
    """Actualiza campos de la mesa, manteniendo la unicidad del nombre."""
    try:
        table_db = session.get(Table, table_id)



        # Validación de capacidad (si se proporciona)
        if table_data.capacity is not None:
            if capacity_table_max := 20:
                if table_data.capacity > capacity_table_max or table_data.capacity <= 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST, 
                        detail=f"La capacidad de la mesa debe ser un número positivo y no mayor a {capacity_table_max}."
                    )
        
        # Validación: La mesa debe existir y no estar eliminada
        if not table_db or table_db.deleted is True:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Mesa no encontrada o eliminada."
            )
        
        data_to_update = table_data.model_dump(exclude_unset=True)
        
        # Validación de unicidad si se intenta cambiar el nombre
        if "name" in data_to_update and data_to_update["name"] != table_db.name:
            # >>> CAMBIO 6: Filtra por 'deleted == False'
            existing_table = session.exec(
                select(Table)
                .where(Table.name == data_to_update["name"])
                .where(Table.deleted == False)
            ).first()
            
            # Si el nombre existe Y no pertenece a la mesa que estamos actualizando
            if existing_table and existing_table.id != table_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ya existe otra mesa activa con el nombre/número: '{data_to_update['name']}'."
                )
        
        # Aplicar actualización y actualizar timestamp
        table_db.sqlmodel_update(data_to_update)
        table_db.updated_at = datetime.utcnow()
        
        session.add(table_db)
        session.commit()
        session.refresh(table_db)
        return table_db
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar la mesa: {str(e)}",
        )

# ----------------------------------------------------------------------
# ENDPOINT 6: ELIMINAR MESA (DELETE /tables/{table_id}) - SOFT DELETE
# ----------------------------------------------------------------------
@router.delete("/{table_id}", status_code=status.HTTP_200_OK, response_model=dict, summary="Realiza la eliminación suave de una mesa")
def soft_delete_table(table_id: int, session: SessionDep):
    """Realiza la 'Eliminación Suave' de una mesa, marcando 'deleted=True', y devuelve un JSON de confirmación."""
    try:
        table_db = session.get(Table, table_id)

        if not table_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Mesa no encontrada."
            )
        
        # Solo permite eliminar si no está ya eliminada 
        if table_db.deleted is True:
            return {"message": f"La Mesa (ID: {table_id}) ya estaba marcada como eliminada."}

        current_time = datetime.utcnow()

        # Aplicar Soft Delete
        table_db.deleted = True
        table_db.deleted_on = current_time
        table_db.updated_at = current_time
        session.add(table_db)
        session.commit()
        
        # Devolvemos el mensaje de éxito en JSON
        return {"message": f"{table_db.name} (ID: {table_id}) ha sido eliminada exitosamente el {current_time.isoformat()}."}
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar la mesa: {str(e)}",
        )
# ----------------------------------------------------------------------
# ENDPOINT 7: RESTAURAR MESA (PATCH /tables/{table_id}/restore)
# ----------------------------------------------------------------------
@router.patch("/{table_id}/restore", response_model=TableRead, summary="Restaura una mesa previamente eliminada")
def restore_deleted_table(table_id: int, session: SessionDep):
    """
    Restaura una mesa previamente eliminada (Soft Delete), 
    cambiando 'deleted' a False y limpiando 'deleted_on', y valida unicidad del nombre.
    """
    try:
        table_db = session.get(Table, table_id)

        if not table_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Mesa no encontrada."
            )
        
        # Solo permite la restauración si está actualmente eliminada
        if table_db.deleted is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="La mesa no está eliminada y no puede ser restaurada."
            )

        # Validación de unicidad: Verificar si el nombre está ocupado por otra mesa activa
        existing_table = session.exec(
            select(Table)
            .where(Table.name == table_db.name)
            .where(Table.deleted == False)
        ).first()

        if existing_table:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail=f"Conflicto: No se puede restaurar. El nombre '{table_db.name}' ya está en uso por otra mesa activa (ID: {existing_table.id})."
            )

        current_time = datetime.utcnow()

        # Restaurar la mesa
        table_db.deleted = False
        table_db.deleted_on = None  # Limpia la marca de tiempo de eliminación
        table_db.updated_at = current_time 

        session.add(table_db)
        session.commit()
        session.refresh(table_db)

        return table_db
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al restaurar la mesa: {str(e)}",
        )
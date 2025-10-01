from fastapi import APIRouter, Depends, status, HTTPException
from sqlmodel import select
from datetime import datetime
from typing import List

# Importa las dependencias del Core
from core.database import SessionDep
from core.security import decode_token 

from models.tables import Table
from schemas.tables_schema import TableCreate, TableRead, TableUpdate 

# Configuración del Router
# Uso 'TABLES' como tag para agrupar en la documentación de la API (Swagger/Redoc)
router = APIRouter(tags=["TABLES"]) 


# Rutas para lectura (GET)
@router.get("/api/tables", response_model=List[TableRead], dependencies=[Depends(decode_token)])
def list_tables(session: SessionDep):
    """
    Obtiene una lista de todas las mesas **activas** (no eliminadas).
    """
    try:
        # Filtra por mesas donde deleted_at es NULL (no eliminadas)
        statement = select(Table).where(Table.deleted_at == None)
        return session.exec(statement).all()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar las mesas: {str(e)}",
        )

@router.get("/api/tables/{table_id}", response_model=TableRead, dependencies=[Depends(decode_token)])
def read_table(table_id: int, session: SessionDep):
    """Obtiene una mesa específica por su ID."""
    try:
        table_db = session.get(Table, table_id)
        
        # Validación de existencia y de eliminación suave
        if not table_db or table_db.deleted_at is not None:
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

# Ruta para creacion (CREATE)
@router.post("/api/tables", response_model=TableRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(decode_token)])
def create_table(table_data: TableCreate, session: SessionDep):
    """Crea una nueva mesa, validando que el nombre sea único."""
    try:
        # Validación de Unicidad por nombre (solo para registros activos)
        existing_table = session.exec(
            select(Table)
            .where(Table.name == table_data.name)
            .where(Table.deleted_at == None)
        ).first()
        if existing_table:
            raise HTTPException(
               status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ya existe una mesa activa con el nombre/número: '{table_data.name}'." 
            )

        # Creación de la Mesa
        table_db = Table.model_validate(table_data.model_dump())
        table_db.created_at = datetime.utcnow()
        table_db.updated_at = datetime.utcnow()

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

# Rutas para actualizar (PATCH)
@router.patch("/api/tables/{table_id}", response_model=TableRead, dependencies=[Depends(decode_token)])
def update_table(table_id: int, table_data: TableUpdate, session: SessionDep):
    """Actualiza campos de la mesa, manteniendo la unicidad del nombre."""
    try:
        table_db = session.get(Table, table_id)

        # Validación: La mesa debe existir y no estar eliminada
        if not table_db or table_db.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Mesa no encontrada o eliminada."
            )
        
        data_to_update = table_data.model_dump(exclude_unset=True)
        
        # Validación de unicidad si se intenta cambiar el nombre
        if "name" in data_to_update and data_to_update["name"] != table_db.name:
            existing_table = session.exec(
                select(Table)
                .where(Table.name == data_to_update["name"])
                .where(Table.deleted_at == None)
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

# Ruta para eliminacion (DELETE - Soft Delete)
@router.delete("/api/tables/{table_id}", status_code=status.HTTP_200_OK, response_model=dict, dependencies=[Depends(decode_token)])
def delete_table(table_id: int, session: SessionDep):
    """Realiza la 'Eliminación Suave' de una mesa."""
    try:
        table_db = session.get(Table, table_id)

        if not table_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Mesa no encontrada."
            )
        
        if table_db.deleted_at is not None:
            return {"message": f"La Mesa (ID: {table_id}) ya estaba marcada como eliminada."}

        current_time = datetime.utcnow()

        # Aplicar Soft Delete
        table_db.deleted_at = current_time
        table_db.updated_at = current_time
        session.add(table_db)
        session.commit()
        
        return {"message": f"Mesa (ID: {table_id}) eliminada (Soft Delete) exitosamente."}
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar la mesa: {str(e)}",
        )
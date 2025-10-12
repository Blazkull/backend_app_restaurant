from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import select, func
from typing import List, Optional
from datetime import datetime

# Importar dependencias del core
from core.database import SessionDep
from models.tables import Table
from schemas.tables_schema import TableRead, TableListResponse, TableCreate, TableUpdate, TableFilter
from schemas.tables_schema import TableStatusUpdate

router = APIRouter(prefix="/api/tables", tags=["Mesas"])

# ======================================================================
# GET /api/tables - Listar mesas con filtros y paginación
# ======================================================================
@router.get("/", response_model=TableListResponse, summary="Listar mesas con filtros y paginación")
def list_tables(
    session: SessionDep,
    id_location: Optional[int] = Query(None, description="Filtrar por ID de ubicación"),
    id_status: Optional[int] = Query(None, description="Filtrar por ID de estado"),
    min_capacity: Optional[int] = Query(None, description="Filtrar por capacidad mínima"),
    max_capacity: Optional[int] = Query(None, description="Filtrar por capacidad máxima"),
    limit: int = Query(10, ge=1, le=100, description="Cantidad máxima de resultados por página"),
    offset: int = Query(0, ge=0, description="Número de elementos a omitir (para paginación)"),
):
    try:
        query = select(Table).where(Table.deleted == False)

        # Aplicar filtros dinámicos
        if id_location:
            query = query.where(Table.id_location == id_location)
        if id_status:
            query = query.where(Table.id_status == id_status)
        if min_capacity:
            query = query.where(Table.capacity >= min_capacity)
        if max_capacity:
            query = query.where(Table.capacity <= max_capacity)

        # Total de registros que cumplen el filtro
        total_count = len(session.exec(query).all())


        # Paginación
        tables = session.exec(query.offset(offset).limit(limit)).all()

        if not tables:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se encontraron mesas")

        total_pages = (total_count + limit - 1) // limit
        current_page = (offset // limit) + 1

        return TableListResponse(
            items=tables,
            total_count=total_count,
            offset=offset,
            limit=limit,
            total_pages=total_pages,
            current_page=current_page
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error al listar las mesas: {e}")
        raise HTTPException(status_code=500, detail=f"Error al listar las mesas: {e}")


# ======================================================================
# GET /api/tables/{table_id} - Obtener mesa por ID
# ======================================================================
@router.get("/{table_id}", response_model=TableRead, summary="Obtener detalles de una mesa por ID")
def get_table(table_id: int, session: SessionDep):
    try:
        table = session.get(Table, table_id)
        if not table or table.deleted:
            raise HTTPException(status_code=404, detail="Mesa no encontrada")
        return table
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener la mesa: {e}")


# ======================================================================
# POST /api/tables - Crear nueva mesa
# ======================================================================
@router.post("/", response_model=TableRead, status_code=status.HTTP_201_CREATED, summary="Crear una nueva mesa")
def create_table(table_data: TableCreate, session: SessionDep):
    try:
        new_table = Table(**table_data.model_dump())
        session.add(new_table)
        session.commit()
        session.refresh(new_table)
        return new_table
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear la mesa: {e}")


# ======================================================================
# PATCH /api/tables/{table_id} - Actualizar mesa
# ======================================================================
@router.patch("/{table_id}", response_model=TableRead, summary="Actualizar datos de una mesa")
def update_table(table_id: int, table_data: TableUpdate, session: SessionDep):
    try:
        table = session.get(Table, table_id)
        if not table or table.deleted:
            raise HTTPException(status_code=404, detail="Mesa no encontrada")

        update_data = table_data.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No se enviaron campos para actualizar")

        for key, value in update_data.items():
            setattr(table, key, value)

        table.updated_at = datetime.utcnow()
        session.add(table)
        session.commit()
        session.refresh(table)
        return table
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al actualizar la mesa: {e}")


# ======================================================================
# DELETE /api/tables/{table_id} - Soft delete
# ======================================================================
@router.delete("/{table_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar (soft delete) una mesa")
def delete_table(table_id: int, session: SessionDep):
    try:
        table = session.get(Table, table_id)
        if not table or table.deleted:
            raise HTTPException(status_code=404, detail="Mesa no encontrada")

        table.deleted = True
        table.deleted_on = datetime.utcnow()
        table.updated_at = datetime.utcnow()

        session.add(table)
        session.commit()
        return
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar la mesa: {e}")


# ======================================================================
# PATCH /api/tables/{table_id}/status - Actualizar solo el estado de una mesa
# ======================================================================
@router.patch("/{table_id}/status", response_model=TableRead, summary="Actualizar estado de una mesa")
def update_table_status(table_id: int, status_data: TableStatusUpdate, session: SessionDep):
    try:
        # 1️⃣ Buscar la mesa
        table = session.get(Table, table_id)
        if not table or table.deleted:
            raise HTTPException(status_code=404, detail="Mesa no encontrada")

        # 2️⃣ Verificar si hay cambio de estado
        if table.id_status == status_data.id_status:
            raise HTTPException(
                status_code=400,
                detail="El estado ya es el mismo, no hay cambios que aplicar."
            )

        # 3️⃣ Actualizar estado
        table.id_status = status_data.id_status
        table.updated_at = datetime.utcnow()

        session.add(table)
        session.commit()
        session.refresh(table)

        return table

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al actualizar el estado de la mesa: {e}")

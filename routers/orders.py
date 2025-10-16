from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import select, col, func
from datetime import datetime
from typing import Optional

# Core
from core.database import SessionDep
from core.security import decode_token

# Modelos
from models.menu_items import MenuItem
from models.orders import Order
from models.order_items import OrderItems
from models.status import Status

# Schemas
from schemas.orders_schema import (
    OrderCreate,
    OrderCreateEmpty,
    OrderRead,
    OrderUpdate
)

router = APIRouter(
    prefix="/api/orders",
    tags=["ORDERS"],
    dependencies=[Depends(decode_token)]
)

# ==========================================================
# GET → Listar órdenes con filtros y metadatos
# ==========================================================
@router.get("", status_code=status.HTTP_200_OK)
def list_orders(
    session: SessionDep,
    id_table: Optional[int] = Query(None, description="Filtrar por mesa"),
    id_status: Optional[int] = Query(None, description="Filtrar por estado de la orden"),
    deleted: Optional[bool] = Query(False, description="Incluir eliminadas si es True"),
    created_from: Optional[datetime] = Query(None, description="Desde fecha de creación"),
    created_to: Optional[datetime] = Query(None, description="Hasta fecha de creación"),
    limit: int = Query(20, ge=1, le=100, description="Límite de resultados"),
    offset: int = Query(0, ge=0, description="Desplazamiento")
):
    """Lista las órdenes con filtros, paginación y metadatos."""
    try:
        query = select(Order).where(Order.deleted == deleted)

        if id_table:
            query = query.where(col(Order.id_table) == id_table)
        if id_status:
            query = query.where(col(Order.id_status) == id_status)
        if created_from:
            query = query.where(col(Order.created_at) >= created_from)
        if created_to:
            query = query.where(col(Order.created_at) <= created_to)

        total_count = session.exec(
            select(func.count()).select_from(query.subquery())
        ).one()

        orders = session.exec(query.limit(limit).offset(offset)).all()

        return {
            "data": orders,
            "metadata": {
                "total_count": total_count,
                "limit": limit,
                "offset": offset
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar las órdenes: {str(e)}"
        )

# ==========================================================
# GET → Obtener una orden específica
# ==========================================================
@router.get("/{order_id}", response_model=OrderRead)
def read_order(order_id: int, session: SessionDep):
    """Obtiene una orden específica por su ID."""
    order = session.get(Order, order_id)
    if not order or order.deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Orden no encontrada o eliminada."
        )
    return order

# ==========================================================
# POST → Crear una orden vacía (sin ítems)
# ==========================================================
@router.post("/create-empty", status_code=status.HTTP_201_CREATED)
def create_empty_order(order_data: OrderCreateEmpty, session: SessionDep):
    """Crea una orden vacía asociada a una mesa y mesero."""
    try:
        new_order = Order(
            id_table=order_data.id_table,
            id_status=order_data.id_status,
            id_user_created=order_data.id_user_created,
            total_value=0.0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        session.add(new_order)
        session.commit()
        session.refresh(new_order)

        return {
            "message": "Orden vacía creada correctamente",
            "order_id": new_order.id,
            "id_table": new_order.id_table,
            "id_status": new_order.id_status
        }

    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Error al crear la orden vacía: {str(e)}"
        )

# ==========================================================
# POST → Crear una nueva orden con ítems
# ==========================================================
@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def create_order(order_data: OrderCreate, session: SessionDep):
    """Crea una nueva orden y sus ítems asociados."""
    try:
        now = datetime.utcnow()

        # Crear la orden principal
        order_data_for_db = order_data.model_dump(exclude={"items"})
        order_db = Order.model_validate(order_data_for_db)
        order_db.created_at = now
        order_db.updated_at = now

        session.add(order_db)
        session.flush()  # Para obtener el ID antes de los ítems

        db_items = []
        total_value = 0.0

        # Crear los ítems asociados
        for item_data in order_data.items:
            menu_item = session.get(MenuItem, item_data.id_menu_item)
            if not menu_item or menu_item.id_status != 1:
                raise HTTPException(
                    status_code=404,
                    detail=f"Plato ID {item_data.id_menu_item} no encontrado o inactivo."
                )

            db_item = OrderItems(
                id_order=order_db.id,
                id_menu_item=item_data.id_menu_item,
                quantity=item_data.quantity,
                note=item_data.note,
                price_at_order=menu_item.price,
                created_at=now,
                updated_at=now,
            )

            session.add(db_item)
            db_items.append(db_item)
            total_value += db_item.price_at_order * db_item.quantity

        # Actualizar el valor total
        order_db.total_value = total_value
        order_db.updated_at = now

        session.commit()
        session.refresh(order_db)

        return order_db

    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear la orden: {str(e)}"
        )

# ==========================================================
# PATCH → Restaurar una orden eliminada
# ==========================================================
@router.patch("/{order_id}/restore", response_model=OrderRead)
def restore_order(order_id: int, session: SessionDep):
    """Restaura una orden eliminada."""
    try:
        order_db = session.get(Order, order_id)
        if not order_db:
            raise HTTPException(status_code=404, detail="Orden no encontrada.")
        if not order_db.deleted:
            raise HTTPException(status_code=400, detail="La orden no está eliminada.")

        now = datetime.utcnow()
        order_db.deleted = False
        order_db.deleted_on = None
        order_db.updated_at = now

        session.add(order_db)
        session.commit()
        session.refresh(order_db)

        return order_db

    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al restaurar la orden: {str(e)}"
        )

# ==========================================================
# PATCH → Actualizar solo el estado de una orden
# ==========================================================
@router.patch("/{order_id}/status", status_code=status.HTTP_200_OK)
def update_order_status(
    order_id: int,
    session: SessionDep,
    id_status: int = Query(..., description="ID del nuevo estado de la orden"),
):
    """Actualiza únicamente el estado (id_status) de una orden."""
    try:
        order = session.get(Order, order_id)
        if not order or order.deleted:
            raise HTTPException(status_code=404, detail="Orden no encontrada o eliminada.")

        status_obj = session.exec(
            select(Status).where(Status.id == id_status, Status.deleted == False)
        ).first()
        if not status_obj:
            raise HTTPException(
                status_code=404,
                detail=f"El estado con id={id_status} no existe."
            )

        order.id_status = id_status
        order.updated_at = datetime.utcnow()

        session.add(order)
        session.commit()
        session.refresh(order)

        return {
            "message": f"Estado de la orden #{order.id} actualizado correctamente.",
            "order_id": order.id,
            "new_status": {
                "id": status_obj.id,
                "name": status_obj.name,
                "description": status_obj.description
            },
            "updated_at": order.updated_at
        }

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al actualizar el estado: {str(e)}"
        )

# ==========================================================
# DELETE → Eliminación suave (Soft Delete)
# ==========================================================
@router.delete("/{order_id}", response_model=dict)
def soft_delete_order(order_id: int, session: SessionDep):
    """Marca una orden y sus ítems como eliminados."""
    try:
        order_db = session.get(Order, order_id)
        if not order_db:
            raise HTTPException(status_code=404, detail="Orden no encontrada.")

        if order_db.deleted:
            return {"message": "La orden ya estaba eliminada."}

        now = datetime.utcnow()
        order_db.deleted = True
        order_db.deleted_on = now
        order_db.updated_at = now
        session.add(order_db)

        session.commit()
        return {"message": f"Orden {order_id} eliminada correctamente."}

    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al eliminar la orden: {str(e)}"
        )

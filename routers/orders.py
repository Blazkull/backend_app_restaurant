from fastapi import APIRouter, Depends, status, HTTPException
from sqlmodel import select
from datetime import datetime
from typing import List

# Importaciones del Core
from core.database import SessionDep
from core.security import decode_token

# Modelos
from models.orders import Order
from models.order_items import OrderItems

# Schemas
from schemas.orders_schema import OrderCreate, OrderRead, OrderUpdate

# Configuración del router
router = APIRouter(
    prefix="/api/orders",
    tags=["ORDERS"],
    dependencies=[Depends(decode_token)]
)

# ==========================================================================
# GET → Listar todas las órdenes activas
# ==========================================================================
@router.get("", response_model=List[OrderRead])
def list_orders(session: SessionDep):
    """Obtiene una lista de todas las órdenes activas (deleted=False), incluyendo sus ítems."""
    try:
        statement = select(Order).where(Order.deleted == False)
        orders = session.exec(statement).all()
        return orders
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar las órdenes: {str(e)}",
        )

# ==========================================================================
# GET → Obtener una orden específica
# ==========================================================================
@router.get("/{order_id}", response_model=OrderRead)
def read_order(order_id: int, session: SessionDep):
    """Obtiene una orden específica por su ID (solo si no está eliminada)."""
    try:
        order_db = session.get(Order, order_id)
        if not order_db or order_db.deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Orden no encontrada o eliminada."
            )
        return order_db
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al leer la orden: {str(e)}",
        )

# ==========================================================================
# POST → Crear una nueva orden
# ==========================================================================
@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def create_order(order_data: OrderCreate, session: SessionDep):
    """Crea una nueva orden y sus ítems asociados dentro de una transacción."""
    try:
        order_db = Order.model_validate(order_data.model_dump(exclude={"items"}))
        now = datetime.utcnow()
        order_db.created_at = now
        order_db.updated_at = now
        session.add(order_db)
        session.flush()  # Para obtener el ID antes de insertar los ítems

        # Crear los ítems asociados
        for item_data in order_data.items:
            item = OrderItems.model_validate(item_data.model_dump())
            item.id_order = order_db.id
            item.created_at = now
            item.updated_at = now
            session.add(item)

        session.commit()
        session.refresh(order_db)
        return order_db
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear la orden: {str(e)}",
        )

# ==========================================================================
# PATCH → Actualizar una orden existente
# ==========================================================================
@router.patch("/{order_id}", response_model=OrderRead)
def update_order(order_id: int, order_data: OrderUpdate, session: SessionDep):
    """Actualiza los campos de una orden (id_table, id_status, etc.)."""
    try:
        order_db = session.get(Order, order_id)
        if not order_db or order_db.deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Orden no encontrada o eliminada."
            )

        data_to_update = order_data.model_dump(exclude_unset=True)
        order_db.sqlmodel_update(data_to_update)
        order_db.updated_at = datetime.utcnow()

        session.add(order_db)
        session.commit()
        session.refresh(order_db)
        return order_db
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar la orden: {str(e)}",
        )

# ==========================================================================
# DELETE → Eliminación suave (Soft Delete)
# ==========================================================================
@router.delete("/{order_id}", response_model=dict)
def soft_delete_order(order_id: int, session: SessionDep):
    """Marca una orden y sus ítems como eliminados (soft delete)."""
    try:
        order_db = session.get(Order, order_id)
        if not order_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Orden no encontrada."
            )
        if order_db.deleted:
            return {"message": f"La orden (ID: {order_id}) ya estaba eliminada."}

        now = datetime.utcnow()

        # Marcar la orden como eliminada
        order_db.deleted = True
        order_db.deleted_on = now
        order_db.updated_at = now
        session.add(order_db)

        # Marcar ítems asociados como eliminados
        items = session.exec(
            select(OrderItems).where(
                OrderItems.id_order == order_id,
                OrderItems.deleted == False
            )
        ).all()

        for item in items:
            item.deleted = True
            item.deleted_on = now
            item.updated_at = now
            session.add(item)

        session.commit()
        return {
            "message": f"Orden (ID: {order_id}) y {len(items)} ítems eliminados correctamente el {now.isoformat()}."
        }
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar la orden: {str(e)}",
        )

# ==========================================================================
# PATCH → Restaurar una orden eliminada
# ==========================================================================
@router.patch("/{order_id}/restore", response_model=OrderRead)
def restore_deleted_order(order_id: int, session: SessionDep):
    """Restaura una orden y sus ítems previamente eliminados (soft restore)."""
    try:
        order_db = session.get(Order, order_id)
        if not order_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Orden no encontrada."
            )
        if not order_db.deleted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La orden no está eliminada."
            )

        now = datetime.utcnow()
        order_db.deleted = False
        order_db.deleted_on = None
        order_db.updated_at = now
        session.add(order_db)

        items = session.exec(
            select(OrderItems).where(
                OrderItems.id_order == order_id,
                OrderItems.deleted == True
            )
        ).all()

        for item in items:
            item.deleted = False
            item.deleted_on = None
            item.updated_at = now
            session.add(item)

        session.commit()
        session.refresh(order_db)
        return order_db
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al restaurar la orden: {str(e)}",
        )

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone
from typing import List, Optional

# Dependencias del core
from core.database import SessionDep
from models.orders import Order
from models.order_items import OrderItems
from models.status import Status
from models.tables import Table

router = APIRouter()

# ================================================================
# PANEL DE COCINA — COMANDAS
# ================================================================

@router.get("/kitchen/orders/", tags=["Cocina"])
def get_kitchen_orders(
    session: SessionDep,
    status_filter: Optional[List[str]] = Query(None, description="Filtrar por estados (Pendiente, Preparación, Listo, Entregado)")
):
    """
    Retorna las órdenes agrupadas por estado para el panel de cocina.
    Si no se pasa `status_filter`, retorna todas las órdenes activas.
    """

    query = (
        select(Order)
        .options(
            selectinload(Order.items),
            selectinload(Order.table),
            selectinload(Order.status)
        )
        .where(Order.deleted_on.is_(None))  # corregido según tus modelos
    )

    if status_filter:
        query = query.where(Order.status.has(Status.name.in_(status_filter)))

    orders = session.exec(query).all()

    grouped = {
        "Pendientes": [],
        "En Preparación": [],
        "Listos": [],
        "Entregados": []
    }

    for order in orders:
        state = order.status.name if order.status else "Desconocido"
        order_data = {
            "order_id": order.id,
            "table": order.table.name if order.table else None,
            "created_at": order.created_at,
            "items": [item.name for item in order.items],
            "elapsed_minutes": (
                (datetime.now(timezone.utc) - order.created_at).seconds // 60
                if order.created_at else 0
            )
        }

        if state == "Pendiente":
            grouped["Pendientes"].append(order_data)
        elif state == "Preparación":
            grouped["En Preparación"].append(order_data)
        elif state == "Listo":
            grouped["Listos"].append(order_data)
        elif state == "Entregado":
            grouped["Entregados"].append(order_data)

    return grouped


# ================================================================
# CAMBIO DE ESTADO — ACTUALIZACIÓN DE COMANDA
# ================================================================

@router.patch("/kitchen/orders/{order_id}/status", tags=["Cocina"])
def update_kitchen_order_status(
    order_id: int,
    new_status: str,
    session: SessionDep
):
    """
    Permite cambiar el estado de una orden en cocina.
    Ejemplo de uso:
      - 'Pendiente' -> 'Preparación'
      - 'Preparación' -> 'Listo'
      - 'Listo' -> 'Entregado'
    """

    order = session.get(Order, order_id)
    if not order or order.deleted_on is not None:
        raise HTTPException(status_code=404, detail="Orden no encontrada o eliminada")

    status_obj = session.exec(select(Status).where(Status.name == new_status)).first()
    if not status_obj:
        raise HTTPException(status_code=404, detail=f"Estado '{new_status}' no existe")

    order.id_status = status_obj.id  # corregido campo de estado
    order.updated_at = datetime.now(timezone.utc)

    session.add(order)
    session.commit()
    session.refresh(order)

    return {
        "message": f"Estado de la orden #{order.id} actualizado a '{new_status}'",
        "order_id": order.id,
        "status": new_status
    }


# ================================================================
# DETALLE DE ORDEN (para modal o vista individual)
# ================================================================

@router.get("/kitchen/orders/{order_id}", tags=["Cocina"])
def get_kitchen_order_detail(order_id: int, session: SessionDep):
    """
    Retorna el detalle completo de una orden específica.
    """

    order = session.exec(
        select(Order)
        .options(
            selectinload(Order.items),
            selectinload(Order.table),
            selectinload(Order.status)
        )
        .where(Order.id == order_id, Order.deleted_on.is_(None))
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    return {
        "order_id": order.id,
        "table": order.table.name if order.table else None,
        "status": order.status.name if order.status else None,
        "created_at": order.created_at,
        "items": [
            {"name": item.name, "quantity": item.quantity}
            for item in order.items
        ]
    }

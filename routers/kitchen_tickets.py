from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone
from typing import Optional

# Core
from core.database import SessionDep
from core.security import decode_token

# Models
from models.orders import Order
from models.order_items import OrderItems
from models.status import Status
from models.tables import Table
from models.menu_items import MenuItem

router = APIRouter(
    prefix="/api/kitchen/orders",
    tags=["PANEL DE COCINA"],
    dependencies=[Depends(decode_token)]
)

# ================================================================
# PANEL DE COCINA — COMANDAS (GET /)
# ================================================================

@router.get("/")
def get_kitchen_orders(
    session: SessionDep,
    status: Optional[str] = Query(
        None,
        description="Filtrar por estado (Pendiente, Preparación, Listo, Entregado)"
    )
):
    """
    Retorna las órdenes agrupadas por estado para el panel de cocina.
    - Si se pasa ?status=, devuelve solo las de ese estado.
    - Incluye: número de orden, hora de creación, mesa, ítems (nombre, cantidad, nota)
    - Excluye precios.
    """

    query = (
        select(Order)
        .options(
            selectinload(Order.order_items).selectinload(OrderItems.menu_item),
            selectinload(Order.table),
            selectinload(Order.status)
        )
        .where(Order.deleted_on.is_(None))
    )

    if status:
        query = query.where(Order.status.has(Status.name == status))

    orders = session.exec(query).all()

    if not orders:
        return {"message": "No hay órdenes registradas", "data": []}

    # 🔸 Estructura base de agrupación
    grouped = {
        "Pendiente": [],
        "Preparación": [],
        "Listo": [],
        "Entregado": []
    }

    for order in orders:
        state = order.status.name if order.status else "Desconocido"

        order_data = {
            "order_number": f"Pedido #{order.id}",
            "table": order.table.name if hasattr(order.table, "name") else f"Mesa {order.table.id}",
            "created_at": order.created_at.strftime("%H:%M") if order.created_at else None,
            "items": [
                {
                    "menu_item": item.menu_item.name if item.menu_item else "Sin nombre",
                    "quantity": item.quantity,
                    "note": item.note or ""
                }
                for item in order.order_items
            ]
        }

        # Solo agregamos si el estado es uno de los válidos
        if state in grouped:
            grouped[state].append(order_data)

    # Si hay filtro, devolvemos solo ese grupo
    if status:
        return {
            "status": status,
            "total": len(grouped.get(status, [])),
            "data": grouped.get(status, [])
        }

    # Si no hay filtro, devolvemos todas agrupadas
    return {
        "totals": {k: len(v) for k, v in grouped.items()},
        "data": grouped
    }

# ================================================================
# AVANZAR ESTADO AUTOMÁTICAMENTE (PATCH /{order_id}/next-status)
# ================================================================

@router.patch("/{order_id}/next-status")
def advance_kitchen_order_status(order_id: int, session: SessionDep):
    """
    Cambia automáticamente el estado de la orden al siguiente paso:
      - Pendiente → Preparación
      - Preparación → Listo
      - Listo → Entregado
    """
    order = session.exec(
        select(Order)
        .where(Order.id == order_id, Order.deleted_on.is_(None))
        .options(selectinload(Order.status))
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada o eliminada")

    current_status = order.status
    if not current_status:
        raise HTTPException(status_code=500, detail="La orden no tiene un estado asignado")

    next_status_map = {
        "Pendiente": "Preparación",
        "Preparación": "Listo",
        "Listo": "Entregado"
    }

    next_status_name = next_status_map.get(current_status.name)
    if not next_status_name:
        raise HTTPException(status_code=400, detail="La orden ya está en el último estado o estado inválido")

    next_status = session.exec(select(Status).where(Status.name == next_status_name)).first()
    if not next_status:
        raise HTTPException(status_code=404, detail=f"El estado '{next_status_name}' no está configurado")

    order.id_status = next_status.id
    order.updated_at = datetime.now(timezone.utc)

    session.add(order)
    session.commit()
    session.refresh(order)

    return {
        "message": f"Orden #{order.id} pasó de '{current_status.name}' a '{next_status_name}'",
        "order_id": order.id,
        "previous_status": current_status.name,
        "new_status": next_status_name
    }

# ================================================================
# DEVOLVER ESTADO ANTERIOR AUTOMÁTICAMENTE (PATCH /{order_id}/previous-status)
# ================================================================

@router.patch("/{order_id}/previous-status")
def revert_kitchen_order_status(order_id: int, session: SessionDep):
    """
    Devuelve automáticamente el estado de la orden al anterior:
      - Entregado → Listo
      - Listo → Preparación
      - Preparación → Pendiente
    """
    order = session.exec(
        select(Order)
        .where(Order.id == order_id, Order.deleted_on.is_(None))
        .options(selectinload(Order.status))
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada o eliminada")

    current_status = order.status
    if not current_status:
        raise HTTPException(status_code=500, detail="La orden no tiene un estado asignado")

    previous_status_map = {
        "Entregado": "Listo",
        "Listo": "Preparación",
        "Preparación": "Pendiente"
    }

    previous_status_name = previous_status_map.get(current_status.name)
    if not previous_status_name:
        raise HTTPException(status_code=400, detail="La orden ya está en el primer estado o estado inválido")

    previous_status = session.exec(select(Status).where(Status.name == previous_status_name)).first()
    if not previous_status:
        raise HTTPException(status_code=404, detail=f"El estado '{previous_status_name}' no está configurado")

    order.id_status = previous_status.id
    order.updated_at = datetime.now(timezone.utc)

    session.add(order)
    session.commit()
    session.refresh(order)

    return {
        "message": f"Orden #{order.id} regresó de '{current_status.name}' a '{previous_status_name}'",
        "order_id": order.id,
        "previous_status": current_status.name,
        "new_status": previous_status_name
    }

# ================================================================
# DETALLE DE UNA ORDEN ESPECÍFICA (GET /{order_id})
# ================================================================

@router.get("/{order_id}")
def get_kitchen_order(order_id: int, session: SessionDep):
    """
    Devuelve el detalle de una orden específica para el panel de cocina.
    Incluye número de orden, hora, mesa y los ítems con cantidad y nota.
    """
    order = session.exec(
        select(Order)
        .where(Order.id == order_id)
        .options(
            selectinload(Order.order_items).selectinload(OrderItems.menu_item),
            selectinload(Order.table)
        )
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    return {
        "numero_orden": f"Pedido #{order.id}",
        "hora_creacion": order.created_at.strftime("%H:%M:%S") if order.created_at else None,
        "mesa": order.table.name if hasattr(order.table, "name") else f"Mesa {order.table.id}",
        "items": [
            {
                "menu_item": item.menu_item.name if item.menu_item else "Ítem no encontrado",
                "cantidad": item.quantity,
                "nota": item.note or ""
            }
            for item in order.order_items
        ]
    }

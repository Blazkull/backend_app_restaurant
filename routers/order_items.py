from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.params import Query
from sqlmodel import col, select
from datetime import datetime
from typing import List, Optional

# --- Core ---
from core.database import SessionDep
from core.security import decode_token

# --- Modelos ---
from models.order_items import OrderItems
from models.orders import Order
from models.menu_items import MenuItem

# --- Schemas ---
from schemas.order_items_schema import (
    OrderItemRead,
    OrderItemCreate,
    OrderItemUpdate,
    OrderItemBulkCreate
)

router = APIRouter(
    prefix="/api/order_items",
    tags=["ORDER ITEMS"],
    dependencies=[Depends(decode_token)]
)

# ===================================================================
# GET → Listar todos los ítems de pedido (activos)
# ===================================================================
@router.get("", status_code=status.HTTP_200_OK)
def list_order_items(
    session: SessionDep,
    id_order: Optional[int] = Query(None, description="Filtrar por ID de orden"),
    id_menu_item: Optional[int] = Query(None, description="Filtrar por ID de ítem de menú"),
    status_item: Optional[str] = Query(None, description="Filtrar por estado del ítem"),
    created_from: Optional[datetime] = Query(None, description="Filtrar desde fecha de creación"),
    created_to: Optional[datetime] = Query(None, description="Filtrar hasta fecha de creación"),
    limit: int = Query(20, description="Límite de resultados por página"),
    offset: int = Query(0, description="Desplazamiento para paginación")
):
    """
    Lista los ítems de pedido con filtros opcionales y metadatos de paginación.
    """
    try:
        query = select(OrderItems)

        if id_order:
            query = query.where(col(OrderItems.id_order) == id_order)
        if id_menu_item:
            query = query.where(col(OrderItems.id_menu_item) == id_menu_item)
        if status_item:
            query = query.where(col(OrderItems.status) == status_item)
        if created_from:
            query = query.where(col(OrderItems.created_at) >= created_from)
        if created_to:
            query = query.where(col(OrderItems.created_at) <= created_to)

        total_count = session.exec(query).count()  # ✅ más óptimo
        query = query.limit(limit).offset(offset)

        items = session.exec(query).all()

        return {
            "data": items,
            "metadata": {
                "total_count": total_count,
                "limit": limit,
                "offset": offset
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar ítems de orden: {str(e)}",
        )


# ===================================================================
# GET → Obtener ítem por ID
# ===================================================================
@router.get("/{item_id}", response_model=OrderItemRead)
def get_order_item(item_id: int, session: SessionDep):
    """Obtiene un ítem de pedido específico por su ID."""
    item = session.get(OrderItems, item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ítem de orden no encontrado."
        )
    return item

# ===================================================================
# POST → Crear ítem individual
# ===================================================================
@router.post("", response_model=OrderItemRead, status_code=status.HTTP_201_CREATED)
def create_order_item(item_data: OrderItemCreate, session: SessionDep):
    """Crea un nuevo ítem para una orden existente."""
    order = session.get(Order, item_data.id_order)
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada.")

    menu_item = session.get(MenuItem, item_data.id_menu_item)
    if not menu_item or menu_item.id_status != 1:
        raise HTTPException(status_code=404, detail="Plato no encontrado o inactivo.")

    # Crear ítem
    item_db = OrderItems.model_validate(item_data.model_dump())
    item_db.price_at_order = menu_item.price
    item_db.created_at = datetime.utcnow()
    item_db.updated_at = datetime.utcnow()

    session.add(item_db)
    session.flush()

    # Actualizar valor total de la orden
    order.total_value += item_db.price_at_order * item_db.quantity
    order.updated_at = datetime.utcnow()
    session.add(order)

    session.commit()
    session.refresh(item_db)
    return item_db

# ===================================================================
# POST → Crear múltiples ítems (bulk)
# ===================================================================
@router.post("/bulk", response_model=List[OrderItemRead], status_code=status.HTTP_201_CREATED)
def create_order_items_bulk(bulk_data: OrderItemBulkCreate, session: SessionDep):
    """Crea múltiples ítems para una orden y actualiza el valor total."""
    order = session.get(Order, bulk_data.id_order)
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada.")

    db_items = []
    total_value = 0.0

    for item_data in bulk_data.items:
        menu_item = session.get(MenuItem, item_data.id_menu_item)
        if not menu_item or menu_item.id_status != 1:
            raise HTTPException(status_code=404, detail=f"Plato ID {item_data.id_menu_item} no encontrado o inactivo.")

        db_item = OrderItems(
            id_order=bulk_data.id_order,
            id_menu_item=item_data.id_menu_item,
            quantity=item_data.quantity,
            note=item_data.note,
            price_at_order=menu_item.price,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(db_item)
        db_items.append(db_item)
        total_value += db_item.price_at_order * db_item.quantity

    order.total_value += total_value
    order.updated_at = datetime.utcnow()
    session.add(order)
    session.commit()

    for db_item in db_items:
        session.refresh(db_item)

    return db_items

# ===================================================================
# PUT → Reemplazar completamente un ítem
# ===================================================================
@router.put("/{item_id}", response_model=OrderItemRead)
def replace_order_item(item_id: int, item_data: OrderItemCreate, session: SessionDep):
    """Reemplaza completamente un ítem existente."""
    item_db = session.get(OrderItems, item_id)
    if not item_db:
        raise HTTPException(status_code=404, detail="Ítem de orden no encontrado.")

    menu_item = session.get(MenuItem, item_data.id_menu_item)
    if not menu_item or menu_item.id_status != 1:
        raise HTTPException(status_code=404, detail="Plato no encontrado o inactivo.")

    order = session.get(Order, item_data.id_order)
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada.")

    # Ajustar total de la orden
    old_value = item_db.quantity * item_db.price_at_order
    new_value = item_data.quantity * menu_item.price
    order.total_value += new_value - old_value

    # Reemplazar datos
    item_db.id_order = item_data.id_order
    item_db.id_menu_item = item_data.id_menu_item
    item_db.quantity = item_data.quantity
    item_db.note = item_data.note
    item_db.price_at_order = menu_item.price
    item_db.updated_at = datetime.utcnow()

    session.add(item_db)
    session.add(order)
    session.commit()
    session.refresh(item_db)

    return item_db

# ===================================================================
# PATCH → Actualizar parcialmente un ítem
# ===================================================================
@router.patch("/{item_id}", response_model=OrderItemRead)
def update_order_item(item_id: int, item_data: OrderItemUpdate, session: SessionDep):
    """Actualiza parcialmente los datos de un ítem."""
    item_db = session.get(OrderItems, item_id)
    if not item_db:
        raise HTTPException(status_code=404, detail="Ítem de orden no encontrado.")

    order = session.get(Order, item_db.id_order)
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada.")

    old_total = item_db.quantity * item_db.price_at_order

    update_data = item_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item_db, key, value)

    # Si se cambió el ítem de menú, actualizar precio
    if "id_menu_item" in update_data:
        menu_item = session.get(MenuItem, item_db.id_menu_item)
        if not menu_item or menu_item.id_status != 1:
            raise HTTPException(status_code=404, detail="Nuevo plato no encontrado o inactivo.")
        item_db.price_at_order = menu_item.price

    new_total = item_db.quantity * item_db.price_at_order
    order.total_value += new_total - old_total
    item_db.updated_at = datetime.utcnow()
    order.updated_at = datetime.utcnow()

    session.add(item_db)
    session.add(order)
    session.commit()
    session.refresh(item_db)

    return item_db

# ===================================================================
# DELETE → Eliminar ítem (Soft Delete)
# ===================================================================
@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order_item(item_id: int, session: SessionDep):
    """Elimina un ítem de una orden (soft delete)."""
    item_db = session.get(OrderItems, item_id)
    if not item_db:
        raise HTTPException(status_code=404, detail="Ítem de orden no encontrado.")

    order = session.get(Order, item_db.id_order)
    if order:
        order.total_value -= item_db.quantity * item_db.price_at_order
        order.updated_at = datetime.utcnow()
        session.add(order)

    session.delete(item_db)
    session.commit()
    return
# ==========================================================================
# GET → Obtener todos los ítems de una orden específica
# ==========================================================================

@router.get("/order/{id_order}", response_model=List[OrderItemRead], status_code=status.HTTP_200_OK)
def get_items_by_order(id_order: int, session: SessionDep):
    """Obtiene todos los ítems de una orden específica"""
    items = session.exec(select(OrderItems).where(OrderItems.id_order == id_order)).all()

    if not items:
        raise HTTPException(status_code=404, detail=f"No se encontraron ítems para la orden {id_order}")

    return items
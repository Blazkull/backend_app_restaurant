from fastapi import APIRouter, Depends, status, HTTPException
from sqlmodel import select
from datetime import datetime
from typing import List

# Importa las dependencias del Core
from core.database import SessionDep
from core.security import decode_token 

from models.orders import Order 
from models.order_items import OrderItem

from schemas.orders_schema import OrderCreate, OrderRead, OrderUpdate 
from schemas.order_items_schema import OrderItemCreate, OrderItemRead 

# Configuración del Router
# Uso 'ORDERS' como tag para agrupar en la documentación de la API (Swagger/Redoc)
router = APIRouter(tags=["ORDERS"]) 


# Rutas para lectura (GET)
@router.get("/api/orders", response_model=List[OrderRead], dependencies=[Depends(decode_token)])
def list_orders(session: SessionDep):
    """
    Obtiene una lista de todas las ordenes **activas** (no eliminadas), 
    incluyendo sus ítems anidados (modelo OrderRead).
    """
    try:
        # Filtra por ordenes donde deleted_at es NULL (no eliminadas)
        statement = select(Order).where(Order.deleted_at == None)
        orders = session.exec(statement).all()
        return orders
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar las órdenes: {str(e)}",
        )

@router.get("/api/orders/{order_id}", response_model=OrderRead, dependencies=[Depends(decode_token)])
def read_order(order_id: int, session: SessionDep):
    """Obtiene una orden específica por su ID, con validación de existencia y estado."""
    try:
        order_db = session.get(Order, order_id)
        
        # Validación de existencia y de eliminación suave
        if not order_db or order_db.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada o eliminada."
            )
        return order_db
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al leer la orden: {str(e)}",
        )

# Ruta para creacion (CREATE)
@router.post("/api/orders", response_model=OrderRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(decode_token)])
def create_order(order_data: OrderCreate, session: SessionDep):
    """Crea una nueva orden y sus ítems de forma atómica (transacción única)."""
    try:
        # Crear la Orden principal
        # Se excluye la lista 'items' ya que SQLModel no la inserta directamente
        order_db = Order.model_validate(order_data.model_dump(exclude={"items"}))
        order_db.created_at = datetime.utcnow()
        order_db.updated_at = datetime.utcnow()
        session.add(order_db)
        
        # Obliga a la DB a generar el ID de la orden antes del commit (Necesario para la clave foránea de OrderItem)
        session.flush() 

        # Iterar y crear los OrderItems anidados
        for item_data in order_data.items:
            # Crear el OrderItem y asignarle la clave foránea id_order
            order_item = OrderItem.model_validate(item_data.model_dump())
            order_item.id_order = order_db.id
            order_item.created_at = datetime.utcnow()
            order_item.updated_at = datetime.utcnow()
            session.add(order_item)

        session.commit()
        session.refresh(order_db) # Recargar para incluir los OrderItems en la respuesta
        return order_db

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        # Revertir todos los cambios si ocurre un error
        session.rollback() 
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear la orden: {str(e)}",
        )

# Rutas para actualizar (PATCH)
@router.patch("/api/orders/{order_id}", response_model=OrderRead, dependencies=[Depends(decode_token)])
def update_order(order_id: int, order_data: OrderUpdate, session: SessionDep):
    """Actualiza campos principales de la orden (id_table, id_status)."""
    try:
        order_db = session.get(Order, order_id)

        # Validación: La orden debe existir y no estar eliminada
        if not order_db or order_db.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada o eliminada."
            )
        
        # Obtener solo los campos proporcionados para la actualización parcial
        data_to_update = order_data.model_dump(exclude_unset=True)

        # Aplicar actualización y actualizar timestamp
        order_db.sqlmodel_update(data_to_update)
        order_db.updated_at = datetime.utcnow()
        
        session.add(order_db)
        session.commit()
        session.refresh(order_db)
        return order_db
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar la orden: {str(e)}",
        )

# Ruta para eliminacion (DELETE - Soft Delete)
@router.delete("/api/orders/{order_id}", status_code=status.HTTP_200_OK, response_model=dict, dependencies=[Depends(decode_token)])
def delete_order(order_id: int, session: SessionDep):
    """Realiza la 'Eliminación Suave' en la orden principal y en sus ítems asociados."""
    try:
        order_db = session.get(Order, order_id)

        if not order_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada."
            )
        
        if order_db.deleted_at is not None:
            return {"message": f"La Orden (ID: {order_id}) ya estaba marcada como eliminada."}

        current_time = datetime.utcnow()

        # Soft Delete en la Orden principal
        order_db.deleted_at = current_time
        order_db.updated_at = current_time
        session.add(order_db)

        # Soft Delete en cascada a todos los OrderItems activos
        order_items = session.exec(
            select(OrderItem)
            .where(OrderItem.id_order == order_id)
            .where(OrderItem.deleted_at == None)
        ).all()
        
        for item in order_items:
            item.deleted_at = current_time
            item.updated_at = current_time
            session.add(item)

        session.commit()

        return {"message": f"Orden (ID: {order_id}) y sus {len(order_items)} ítems asociados eliminados (Soft Delete) exitosamente."}
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar la orden: {str(e)}",
        )
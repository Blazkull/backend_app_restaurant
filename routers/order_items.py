from fastapi import APIRouter, Depends, status, HTTPException
from sqlmodel import select
from datetime import datetime
from typing import List

# Importa las dependencias del Core
from core.database import SessionDep
from core.security import decode_token 

from models.order_items import OrderItem 
# Order (necesario para validar la existencia de la orden padre)
from models.orders import Order 

from schemas.orde_items_schema import OrderItemCreate, OrderItemRead, OrderItemUpdate 

# Configuración del Router
# Uso 'ORDER ITEMS' como tag para agrupar en la documentación de la API (Swagger/Redoc)
router = APIRouter(tags=["ORDER ITEMS"])


# Rutas para lectura (GET)
@router.get("/api/orders/{order_id}/items", response_model=List[OrderItemRead], dependencies=[Depends(decode_token)])
def list_order_items(order_id: int, session: SessionDep):
    """
    Lista todos los ítems activos (no eliminados) de una orden específica.
    """
    # Validación: Verificar que la Orden padre exista y no este eliminada
    order_db = session.get(Order, order_id)
    if not order_db or order_db.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="La orden padre no existe o está eliminada."
        )

    try:
        # Consulta los OrderItems que pertenecen a la orden y no estan eliminados
        statement = (
            select(OrderItem)
            .where(OrderItem.id_order == order_id)
            .where(OrderItem.deleted_at == None)
        )
        return session.exec(statement).all()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar los ítems de la orden: {str(e)}",
        )

@router.get("/api/orders/{order_id}/items/{item_id}", response_model=OrderItemRead, dependencies=[Depends(decode_token)])
def read_order_item(order_id: int, item_id: int, session: SessionDep):
    """Obtiene un OrderItem específico por ID, validando su pertenencia a la orden."""
    # Validación: Verificar que la Orden padre exista
    order_db = session.get(Order, order_id)
    if not order_db or order_db.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="La orden padre no existe o está eliminada."
        )
        
    try:
        order_item_db = session.get(OrderItem, item_id)
        
        # Validación de existencia, soft delete y pertenencia a la orden correcta
        if not order_item_db or order_item_db.deleted_at is not None or order_item_db.id_order != order_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Ítem de la orden no encontrado."
            )
        return order_item_db
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al leer el ítem de la orden: {str(e)}",
        )

# Ruta para creacion (CREATE)
@router.post("/api/orders/{order_id}/items", response_model=OrderItemRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(decode_token)])
def add_item_to_order(order_id: int, item_data: OrderItemCreate, session: SessionDep):
    """Agrega un nuevo ítem a una orden existente."""
    # Validación: Verificar que la Orden padre exista
    order_db = session.get(Order, order_id)
    if not order_db or order_db.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="La orden padre no existe o está eliminada."
        )
        
    try:
        # Crear el OrderItem y establecer la FC
        order_item_db = OrderItem.model_validate(item_data.model_dump())
        order_item_db.id_order = order_id # Asignar el ID de la orden desde la URL
        order_item_db.created_at = datetime.utcnow()
        order_item_db.updated_at = datetime.utcnow()

        session.add(order_item_db)
        session.commit()
        session.refresh(order_item_db)
        
        # Opcional: Actualizar el updated_at de la Orden padre para auditoría
        order_db.updated_at = datetime.utcnow()
        session.add(order_db)
        session.commit() 
        session.refresh(order_item_db) # Asegurar que se obtiene la versión final
        
        return order_item_db

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback() 
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al agregar el ítem a la orden: {str(e)}",
        )

# Rutas para actualizar (PATCH)
@router.patch("/api/orders/{order_id}/items/{item_id}", response_model=OrderItemRead, dependencies=[Depends(decode_token)])
def update_order_item(order_id: int, item_id: int, item_data: OrderItemUpdate, session: SessionDep):
    """Actualiza la cantidad o la nota de un ítem de la orden."""
    # Validación: Verificar que la Orden padre exista
    order_db = session.get(Order, order_id)
    if not order_db or order_db.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="La orden padre no existe o está eliminada."
        )
        
    try:
        order_item_db = session.get(OrderItem, item_id)

        # Validación: El ítem debe existir, no estar eliminado y pertenecer a la orden
        if not order_item_db or order_item_db.deleted_at is not None or order_item_db.id_order != order_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Ítem de la orden no encontrado o no pertenece a esta orden."
            )
        
        data_to_update = item_data.model_dump(exclude_unset=True)

        # Aplicar actualización y actualizar timestamp
        order_item_db.sqlmodel_update(data_to_update)
        order_item_db.updated_at = datetime.utcnow()
        
        session.add(order_item_db)
        session.commit()
        session.refresh(order_item_db)
        
        # Opcional: Actualizar el updated_at de la Orden padre
        order_db.updated_at = datetime.utcnow()
        session.add(order_db)
        session.commit()
        session.refresh(order_item_db)

        return order_item_db
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar el ítem de la orden: {str(e)}",
        )

# Ruta para eliminacion (DELETE - Soft Delete)
@router.delete("/api/orders/{order_id}/items/{item_id}", status_code=status.HTTP_200_OK, response_model=dict, dependencies=[Depends(decode_token)])
def remove_item_from_order(order_id: int, item_id: int, session: SessionDep):
    """Realiza la 'Eliminación Suave' de un ítem de la orden."""
    # Validación: Verificar que la Orden padre exista
    order_db = session.get(Order, order_id)
    if not order_db or order_db.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="La orden padre no existe o está eliminada."
        )
        
    try:
        order_item_db = session.get(OrderItem, item_id)

        # Validación: El ítem debe existir, y pertenecer a la orden
        if not order_item_db or order_item_db.id_order != order_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Ítem de la orden no encontrado o no pertenece a esta orden."
            )
        
        if order_item_db.deleted_at is not None:
            return {"message": f"El ítem (ID: {item_id}) ya estaba marcado como eliminado."}

        current_time = datetime.utcnow()

        # Aplicar Soft Delete
        order_item_db.deleted_at = current_time
        order_item_db.updated_at = current_time
        session.add(order_item_db)
        
        # Actualizar el updated_at de la Orden padre
        order_db.updated_at = current_time
        session.add(order_db)
        
        session.commit()

        return {"message": f"Ítem de la orden (ID: {item_id}) eliminado (Soft Delete) exitosamente."}
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar el ítem de la orden: {str(e)}",
        )
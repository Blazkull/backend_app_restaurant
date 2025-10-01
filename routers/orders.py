from fastapi import APIRouter, Depends, status, HTTPException
from sqlmodel import select
from datetime import datetime
from typing import List

# Importa las dependencias del Core
from core.database import SessionDep
from core.security import decode_token 

from models.orders import Order # Asume que tiene deleted y deleted_on
from models.order_items import OrderItem # Asume que tiene deleted y deleted_on
# Se asume que Table y Status tienen también implementado el soft delete

from schemas.orders_schema import OrderCreate, OrderRead, OrderUpdate 
from schemas.order_items_schema import OrderItemCreate, OrderItemRead 

# Configuración del Router con prefijo y dependencia de autenticación
router = APIRouter(
    prefix="/api/orders", 
    tags=["ORDERS"], 
    dependencies=[Depends(decode_token)]
) 

# --- RUTAS DE LECTURA (GET) ---

@router.get("", response_model=List[OrderRead]) # Ruta: /api/orders
def list_orders(session: SessionDep):
    """
    Obtiene una lista de todas las ordenes **activas** (deleted=False), 
    incluyendo sus ítems anidados.
    """
    try:
        # >>> CAMBIO 1: Filtra por ordenes donde deleted es False
        statement = select(Order).where(Order.deleted == False)
        orders = session.exec(statement).all()
        return orders
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar las órdenes: {str(e)}",
        )

@router.get("/{order_id}", response_model=OrderRead) # Ruta: /api/orders/{order_id}
def read_order(order_id: int, session: SessionDep):
    """Obtiene una orden específica por su ID, con validación de existencia y estado (solo activos)."""
    try:
        order_db = session.get(Order, order_id)
        
        # >>> CAMBIO 2: Validación de existencia y de eliminación suave (deleted is True)
        if not order_db or order_db.deleted is True:
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

# --- RUTA PARA CREACIÓN (POST) ---

@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED) # Ruta: /api/orders
def create_order(order_data: OrderCreate, session: SessionDep):
    """Crea una nueva orden y sus ítems de forma atómica (transacción única)."""
    try:
        # NOTA: Aquí se asume que las validaciones de FKs (id_table, id_status, id_menu_item)
        # se harán en otra capa o se omiten para simplificar este código.

        # Crear la Orden principal
        order_db = Order.model_validate(order_data.model_dump(exclude={"items"}))
        order_db.created_at = datetime.utcnow()
        order_db.updated_at = datetime.utcnow()
        # 'deleted' y 'deleted_on' se establecen por defecto (False y None)
        session.add(order_db)
        
        session.flush() 

        # Iterar y crear los OrderItems anidados
        for item_data in order_data.items:
            order_item = OrderItem.model_validate(item_data.model_dump())
            order_item.id_order = order_db.id
            order_item.created_at = datetime.utcnow()
            order_item.updated_at = datetime.utcnow()
            # 'deleted' y 'deleted_on' se establecen por defecto (False y None)
            session.add(order_item)

        session.commit()
        session.refresh(order_db) 
        return order_db

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback() 
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear la orden: {str(e)}",
        )

# --- RUTA PARA ACTUALIZACIÓN (PATCH) ---

@router.patch("/{order_id}", response_model=OrderRead) # Ruta: /api/orders/{order_id}
def update_order(order_id: int, order_data: OrderUpdate, session: SessionDep):
    """Actualiza campos principales de la orden (id_table, id_status)."""
    try:
        order_db = session.get(Order, order_id)

        # >>> CAMBIO 3: Validación de soft delete (deleted is True)
        if not order_db or order_db.deleted is True:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada o eliminada."
            )
        
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

# --- RUTA PARA ELIMINACIÓN SUAVE (DELETE) ---

@router.delete("/{order_id}", status_code=status.HTTP_200_OK, response_model=dict) # Ruta: /api/orders/{order_id}
def soft_delete_order(order_id: int, session: SessionDep):
    """Realiza la 'Eliminación Suave' en la orden principal y en sus ítems asociados."""
    try:
        order_db = session.get(Order, order_id)

        if not order_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada."
            )
        
        # >>> CAMBIO 4: Usar 'deleted' en lugar de 'deleted_at'
        if order_db.deleted is True:
            return {"message": f"La Orden (ID: {order_id}) ya estaba marcada como eliminada."}

        current_time = datetime.utcnow()

        # Soft Delete en la Orden principal
        # >>> CAMBIO 5: Asignar deleted=True y deleted_on
        order_db.deleted = True
        order_db.deleted_on = current_time
        order_db.updated_at = current_time
        session.add(order_db)

        # Soft Delete en cascada a todos los OrderItems activos
        order_items = session.exec(
            select(OrderItem)
            .where(OrderItem.id_order == order_id)
            # >>> CAMBIO 6: Usar 'deleted = False'
            .where(OrderItem.deleted == False) 
        ).all()
        
        for item in order_items:
            # >>> CAMBIO 7: Asignar deleted=True y deleted_on
            item.deleted = True
            item.deleted_on = current_time
            item.updated_at = current_time
            session.add(item)

        session.commit()

        return {"message": f"Orden (ID: {order_id}) y sus {len(order_items)} ítems asociados eliminados (Soft Delete) exitosamente el {current_time.isoformat()}."}
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar la orden: {str(e)}",
        )

# --- RUTA PARA RESTAURACIÓN (PATCH /restore) ---

@router.patch("/{order_id}/restore", response_model=OrderRead) # Ruta: /api/orders/{order_id}/restore
def restore_deleted_order(order_id: int, session: SessionDep):
    """
    Restaura una orden previamente eliminada (Soft Delete), 
    cambiando 'deleted' a False y limpiando 'deleted_on' en la orden y sus ítems.
    """
    try:
        order_db = session.get(Order, order_id)

        if not order_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada."
            )
        
        # Solo permite la restauración si está actualmente eliminada
        if order_db.deleted is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="La orden no está eliminada y no puede ser restaurada."
            )
            
        current_time = datetime.utcnow()

        # 1. Restaurar la Orden principal
        order_db.deleted = False
        order_db.deleted_on = None  # Limpia la marca de tiempo de eliminación
        order_db.updated_at = current_time 
        session.add(order_db)

        # 2. Restaurar todos los OrderItems que fueron eliminados con la orden
        order_items = session.exec(
            select(OrderItem)
            .where(OrderItem.id_order == order_id)
            .where(OrderItem.deleted == True) 
        ).all()
        
        restored_items_count = 0
        for item in order_items:
            
            item.deleted = False
            item.deleted_on = None
            item.updated_at = current_time
            session.add(item)
            restored_items_count += 1

        session.commit()
        session.refresh(order_db)

        return order_db
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al restaurar la orden: {str(e)}",
        )
from fastapi import APIRouter, Depends, status, HTTPException
from sqlmodel import select
from datetime import datetime
from typing import List

# Importa las dependencias del Core
from core.database import SessionDep
from core.security import decode_token 

from models.order_items import OrderItem 
from models.orders import Order 
from models.menu_items import MenuItem
from schemas.order_items_schema import OrderItemCreate, OrderItemRead, OrderItemUpdate 

# Configuración del Router con prefijo y dependencia de autenticación
router = APIRouter(
    prefix="/api/orders/{order_id}/items", 
    tags=["ORDER ITEMS"], 
    dependencies=[Depends(decode_token)]
)

# --- RUTAS DE LECTURA (GET) ---

@router.get("", response_model=List[OrderItemRead]) # Ruta: /api/orders/{order_id}/items
def list_order_items(order_id: int, session: SessionDep):
    """
    Lista todos los ítems activos (deleted=False) de una orden específica.
    """
    # Validación: Verificar que la Orden padre exista y no esté eliminada
    order_db = session.get(Order, order_id)
    # >>> CAMBIO 1: Usar 'deleted' en lugar de 'deleted_at'
    if not order_db or order_db.deleted is True: 
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="La orden padre no existe o está eliminada."
        )

    try:
        # Consulta los OrderItems que pertenecen a la orden y no estan eliminados
        # >>> CAMBIO 2: Usar 'deleted = False' en lugar de 'deleted_at == None'
        statement = (
            select(OrderItem)
            .where(OrderItem.id_order == order_id)
            .where(OrderItem.deleted == False)
        )
        return session.exec(statement).all()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar los ítems de la orden: {str(e)}",
        )

@router.get("/{item_id}", response_model=OrderItemRead) # Ruta: /api/orders/{order_id}/items/{item_id}
def read_order_item(order_id: int, item_id: int, session: SessionDep):
    """Obtiene un OrderItem específico por ID, validando su pertenencia a la orden y que esté activo."""
    # Validación: Verificar que la Orden padre exista
    order_db = session.get(Order, order_id)
    # >>> CAMBIO 3: Usar 'deleted' en lugar de 'deleted_at'
    if not order_db or order_db.deleted is True:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="La orden padre no existe o está eliminada."
        )
        
    try:
        order_item_db = session.get(OrderItem, item_id)
        
        # Validación de existencia, soft delete y pertenencia a la orden correcta
        # >>> CAMBIO 4: Usar 'deleted' en lugar de 'deleted_at'
        if not order_item_db or order_item_db.deleted is True or order_item_db.id_order != order_id:
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

# --- RUTA PARA CREACIÓN (POST) ---

@router.post("", response_model=OrderItemRead, status_code=status.HTTP_201_CREATED) # Ruta: /api/orders/{order_id}/items
def add_item_to_order(order_id: int, item_data: OrderItemCreate, session: SessionDep):
    """Agrega un nuevo ítem a una orden existente, validando el ítem del menú."""
    # Validación: Verificar que la Orden padre exista y no este eliminada
    # >>> CAMBIO 5: Usar 'deleted' en lugar de 'deleted_at'
    order_db = session.get(Order, order_id)
    if not order_db or order_db.deleted is True:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="La orden padre no existe o está eliminada."
        )
        
    try:
        # Validación: Verificar que el MenuItem exista y no esté eliminado
        if item_data.id_menu_item:
            menu_item_db = session.get(MenuItem, item_data.id_menu_item)
            if not menu_item_db or menu_item_db.deleted is True:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El ítem del menú (ID: {item_data.id_menu_item}) no existe o está eliminado."
                )

        # Crear el OrderItem y establecer la FC
        order_item_db = OrderItem.model_validate(item_data.model_dump())
        order_item_db.id_order = order_id # Asignar el ID de la orden desde la URL
        order_item_db.created_at = datetime.utcnow()
        order_item_db.updated_at = datetime.utcnow()
        # 'deleted' y 'deleted_on' se establecen por defecto en el modelo (False y None)

        session.add(order_item_db)
        session.commit()
        session.refresh(order_item_db)
        
        # Actualizar el updated_at de la Orden padre para auditoría
        order_db.updated_at = datetime.utcnow()
        session.add(order_db)
        session.commit() 
        session.refresh(order_item_db) 
        
        return order_item_db

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback() 
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al agregar el ítem a la orden: {str(e)}",
        )

# --- RUTA PARA ACTUALIZAR (PATCH) ---

@router.patch("/{item_id}", response_model=OrderItemRead) # Ruta: /api/orders/{order_id}/items/{item_id}
def update_order_item(order_id: int, item_id: int, item_data: OrderItemUpdate, session: SessionDep):
    """Actualiza la cantidad o la nota de un ítem de la orden activo."""
    # Validación: Verificar que la Orden padre exista
    order_db = session.get(Order, order_id)
    # >>> CAMBIO 6: Usar 'deleted' en lugar de 'deleted_at'
    if not order_db or order_db.deleted is True:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="La orden padre no existe o está eliminada."
        )
        
    try:
        order_item_db = session.get(OrderItem, item_id)

        # Validación: El ítem debe existir, no estar eliminado y pertenecer a la orden
        # >>> CAMBIO 7: Usar 'deleted' en lugar de 'deleted_at'
        if not order_item_db or order_item_db.deleted is True or order_item_db.id_order != order_id:
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
        
        # Actualizar el updated_at de la Orden padre
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

# --- RUTA PARA ELIMINACIÓN SUAVE (DELETE) ---

@router.delete("/{item_id}", status_code=status.HTTP_200_OK, response_model=dict) # Ruta: /api/orders/{order_id}/items/{item_id}
def remove_item_from_order(order_id: int, item_id: int, session: SessionDep):
    """Realiza la 'Eliminación Suave' de un ítem de la orden."""
    # Validación: Verificar que la Orden padre exista
    order_db = session.get(Order, order_id)
    # >>> CAMBIO 8: Usar 'deleted' en lugar de 'deleted_at'
    if not order_db or order_db.deleted is True:
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
        
        # >>> CAMBIO 9: Usar 'deleted' en lugar de 'deleted_at'
        if order_item_db.deleted is True:
            return {"message": f"El ítem (ID: {item_id}) ya estaba marcado como eliminado."}

        current_time = datetime.utcnow()

        # Aplicar Soft Delete
        # >>> CAMBIO 10: Asignar deleted=True y deleted_on = current_time
        order_item_db.deleted = True
        order_item_db.deleted_on = current_time
        order_item_db.updated_at = current_time
        session.add(order_item_db)
        
        # Actualizar el updated_at de la Orden padre
        order_db.updated_at = current_time
        session.add(order_db)
        
        session.commit()

        return {"message": f"Ítem de la orden (ID: {item_id}) eliminado (Soft Delete) exitosamente el {current_time.isoformat()}."}
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar el ítem de la orden: {str(e)}",
        )


# --- RUTA PARA RESTAURACIÓN (PATCH /restore) ---

@router.patch("/{item_id}/restore", response_model=OrderItemRead) # Ruta: /api/orders/{order_id}/items/{item_id}/restore
def restore_order_item(order_id: int, item_id: int, session: SessionDep):
    """
    Restaura un ítem de orden previamente eliminado (Soft Delete), 
    cambiando 'deleted' a False y limpiando 'deleted_on'.
    """
    # Validación: Verificar que la Orden padre exista y no este eliminada
    order_db = session.get(Order, order_id)
    if not order_db or order_db.deleted is True:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="La orden padre no existe o está eliminada."
        )
        
    try:
        item_db = session.get(OrderItem, item_id)

        # Validación: El ítem debe existir y pertenecer a la orden
        if not item_db or item_db.id_order != order_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Ítem de la orden no encontrado o no pertenece a esta orden."
            )
        
        # Solo permite la restauración si está actualmente eliminado
        if item_db.deleted is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="El ítem de la orden no está eliminado y no puede ser restaurado."
            )
        
        # Validación de FK: El MenuItem debe existir y no estar eliminado para poder restaurar
        if item_db.id_menu_item:
            menu_item_db = session.get(MenuItem, item_db.id_menu_item)
            if not menu_item_db or menu_item_db.deleted is True:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"No se puede restaurar. El Ítem del Menú (ID: {item_db.id_menu_item}) asociado fue eliminado."
                )

        current_time = datetime.utcnow()

        # Restaurar el ítem
        item_db.deleted = False
        item_db.deleted_on = None  # Limpia la marca de tiempo de eliminación
        item_db.updated_at = current_time 

        session.add(item_db)
        
        # Actualizar el updated_at de la Orden padre
        order_db.updated_at = current_time
        session.add(order_db)
        
        session.commit()
        session.refresh(item_db)

        return item_db
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al restaurar el ítem de la orden: {str(e)}",
        )
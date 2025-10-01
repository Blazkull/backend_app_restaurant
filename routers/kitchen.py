from typing import List, Dict, Any, Optional
from datetime import datetime, date, time
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlmodel import Session, select, func, or_, Field, SQLModel, column, outerjoin, selectinload # 💡 selectinload

# Importaciones de Core
from core.database import SessionDep
from core.security import decode_token 

# Importaciones de Modelos y Schemas
from models.orders import Order # Asegúrate que Order tiene la relación 'status'
from models.status import Status 
from schemas.orders_schema import OrderRead, OrderKitchenUpdate # 💡 OrderKitchenUpdate


router = APIRouter(prefix="/kitchen", tags=["Panel de Cocina"])


# ======================================================================
# 1. UTILIDADES Y CONSTANTES
# ======================================================================

def get_status_id_by_name(session: Session, status_name: str) -> int:
    """Busca el ID de un estado dado su nombre."""
    status_db = session.exec(
        select(Status.id).where(Status.name.ilike(status_name))
    ).first()
    
    if not status_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Status name '{status_name}' not recognized."
        )
    return status_db

# CONSTANTES DE ESTADO (Nombres de los estados clave de cocina)
KITCHEN_STATUS_NAMES = ["Pendiente", "En Preparación", "Listo"]


# ======================================================================
# ENDPOINT 1: OBTENER PEDIDOS POR ESTADO (GET /kitchen/orders)
# ======================================================================

@router.get(
    "/orders",
    response_model=List[OrderRead],
    summary="Obtener pedidos para el panel de cocina, filtrados por nombre de estado",
    dependencies=[Depends(decode_token)]
)
def get_kitchen_orders(
    session: SessionDep,
    order_status_name: str = Query( 
        ..., 
        description="Nombre del estado del pedido (ej: 'Pendiente', 'En Preparación')."
    ),
    limit: int = Query(default=10, le=100),
    offset: int = Query(default=0, ge=0),
):
    """
    Retorna la lista de pedidos filtrados por el nombre del estado (solo pedidos de hoy).
    """
    
    target_status_id = get_status_id_by_name(session, order_status_name)
    start_of_day = datetime.combine(date.today(), time.min)
    end_of_day = datetime.combine(date.today(), time.max)

    query = (
        select(Order)
        # 🔑 CARGAR RELACIÓN: Asegura que el objeto Status se incluya en la respuesta OrderRead
        .options(selectinload(Order.status)) 
        
        .where(
            Order.id_status == target_status_id,
            Order.created_at >= start_of_day,
            Order.created_at <= end_of_day
        )
        .order_by(Order.created_at)
        .offset(offset)
        .limit(limit)
    )

    orders = session.exec(query).all()
    
    if not orders and offset > 0:
         raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No more orders found for this status with the given offset."
        )

    return orders

# ======================================================================
# ENDPOINT 2: OBTENER CONTEO DE PEDIDOS POR ESTADO (GET /kitchen/count)
# ======================================================================

@router.get(
    "/count",
    response_model=Dict[str, int],
    summary="Contar pedidos del día por estado (Pendientes, En Preparación, Listos)",
    dependencies=[Depends(decode_token)]
)
def get_kitchen_counts(session: SessionDep) -> Dict[str, int]:
    """
    Retorna el conteo diario, garantizando que los estados clave muestren 0 si no hay pedidos hoy,
    mediante un LEFT OUTER JOIN.
    """
    
    start_of_day = datetime.combine(date.today(), time.min)
    end_of_day = datetime.combine(date.today(), time.max)
    
    date_filter = column("created_at").between(start_of_day, end_of_day)

    statement = (
        select(Status.name, func.count(Order.id).label("order_count"))
        .outerjoin(Order, (Status.id == Order.id_status) & date_filter) 
        .where(Status.name.in_(KITCHEN_STATUS_NAMES)) 
        .group_by(Status.name)
    )
    
    results = session.exec(statement).all()
    
    counts: Dict[str, int] = {}
    
    for status_name, count in results:
        counts[status_name.strip()] = count
        
    for name in KITCHEN_STATUS_NAMES:
        if name not in counts:
            counts[name] = 0

    return counts


# ======================================================================
# ENDPOINT 3: ACTUALIZAR ORDEN COMPLETA (PATCH /kitchen/order/{order_id})
# ======================================================================

@router.patch(
    "/order/{order_id}",
    response_model=OrderRead,
    summary="Actualizar campos y/o el estado de un pedido (por nombre de estado)",
    dependencies=[Depends(decode_token)]
)
def update_order(
    order_id: int, 
    order_data: OrderKitchenUpdate, 
    session: SessionDep
):    
    """
    Actualiza el id_status (resolviendo el nombre) y otros campos opcionales del pedido.
    """
    try:
        order_db = session.get(Order, order_id)

        if not order_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Order with ID {order_id} not found."
            )

        order_data_dict = order_data.model_dump(exclude_unset=True)
        
        # 1. Resolver el ID de estado si se proporcionó el nombre
        if "status_name" in order_data_dict:
            status_name = order_data_dict.pop("status_name")
            new_status_id = get_status_id_by_name(session, status_name)
            
            # Usar el ID resuelto para la actualización
            order_data_dict["id_status"] = new_status_id 
        
        # 2. Actualizar la orden y guardar
        if order_data_dict:
            order_db.sqlmodel_update(order_data_dict)
            order_db.updated_at = datetime.utcnow() 

            session.add(order_db)
            session.commit()
            session.refresh(order_db)

        # 🔑 CARGAR RELACIÓN: Necesario para que el OrderRead de respuesta sea válido
        # Usamos session.exec(select) para cargar las relaciones antes de devolver
        final_order_query = select(Order).where(Order.id == order_id).options(selectinload(Order.status))
        final_order = session.exec(final_order_query).first()
        
        return final_order
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while updating order: {str(e)}",
        )
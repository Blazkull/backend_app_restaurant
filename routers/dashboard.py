from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import select, func
from datetime import datetime, timedelta, date
from typing import Optional, Dict, Any

# Core
from core.database import SessionDep
from core.security import decode_token

# Models
from models.orders import Order
from models.invoices import Invoice
from models.menu_items import MenuItem
from models.order_items import OrderItems
from models.tables import Table
from models.clients import Client
from models.users import User
from models.categories import Category

router = APIRouter(
    prefix="/api/dashboard",
    tags=["DASHBOARD"],
    dependencies=[Depends(decode_token)]
)


@router.get("/summarys")
def get_dashboard_summary(session: SessionDep):
    return {"message": "Dashboard funcionando correctamente"}


# ============================================================
# 1 RESUMEN GENERAL — /api/dashboard/summary
# ============================================================
@router.get("/summary", response_model=Dict[str, Any])
def get_dashboard_summary(session: SessionDep):
    """
    Devuelve un resumen del día actual con:
      - Total de pedidos del día
      - Total de ventas del día
      - Total de clientes activos
      - Mesas ocupadas y disponibles
      - Producto más vendido del día
    """
    try:
        # Fecha actual (sin hora)
        today = date.today()

        # Total de pedidos del día
        total_orders_today = session.exec(select(func.count(Order.id)).where(func.date(Order.created_at) == today)).one()

        # Total de ventas del día
        total_sales_today = session.exec(select(func.coalesce(func.sum(Invoice.total), 0)).where(func.date(Invoice.created_at) == today)).one()

        # Total de clientes activos
        total_clients = session.exec(select(func.count(Client.id)).where(Client.deleted == False)).one()

        # Ocupación de mesas
        occupied_tables = session.exec(select(func.count(Table.id)).where(Table.id_status == 3)).one()

        available_tables = session.exec(select(func.count(Table.id)).where(Table.id_status == 4)).one()

        # Producto más vendido del día
        top_product_query = session.exec(
            select(MenuItem.name, func.sum(OrderItems.quantity).label("total_vendido"))
            .join(OrderItems.menu_item)
            .join(OrderItems.order)
            .where(func.date(Order.created_at) == today)
            .group_by(MenuItem.name)
            .order_by(func.sum(OrderItems.quantity).desc())
            .limit(1)).first()

        top_product = (
            {
                "name": top_product_query[0],
                "quantity_sold": int(top_product_query[1])
            }
            if top_product_query
            else {"name": "Sin ventas", "quantity_sold": 0}
        )

        # Respuesta estructurada
        return {
            "date": today.strftime("%Y-%m-%d"),
            "summary": {
                "orders_today": total_orders_today,
                "sales_today": float(total_sales_today or 0),
                "clients_total": total_clients,
                "tables": {
                    "available": available_tables,
                    "occupied": occupied_tables,
                    "occupancy_rate": (
                        round(
                            (occupied_tables / (occupied_tables + available_tables)) * 100, 2
                        )
                        if (occupied_tables + available_tables) > 0
                        else 0
                    )
                },
                "top_product": top_product
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener el resumen diario: {str(e)}"
        )


# ============================================================
# 2 VENTAS POR RANGO DE TIEMPO — /api/dashboard/sales
# ============================================================
@router.get("/sales", response_model=Dict[str, Any])
def get_sales_summary(
    session: SessionDep,
    range_type: str = Query("mensual", description="Rango de tiempo: 'mensual', 'trimestral' o 'anual'")
):
    """
    Devuelve estadísticas de ventas agrupadas por período (mensual, trimestral o anual).
    """
    try:
        now = datetime.utcnow()

        if range_type == "mensual":
            start_date = now.replace(day=1)
        elif range_type == "trimestral":
            month_start = ((now.month - 1) // 3) * 3 + 1
            start_date = now.replace(month=month_start, day=1)
        elif range_type == "anual":
            start_date = now.replace(month=1, day=1)
        else:
            raise HTTPException(status_code=400, detail="Rango inválido. Use: mensual, trimestral o anual.")

        total_sales = session.exec(
            select(func.sum(Invoice.total))    
            .where(Invoice.created_at >= start_date)
            .where(Invoice.deleted == False)
        ).one()

        count_invoices = session.exec(
            select(func.count(Invoice.id))
            .where(Invoice.created_at >= start_date)
            .where(Invoice.deleted == False)
        ).one()

        return {
            "range": range_type,
            "start_date": start_date.isoformat(),
            "end_date": now.isoformat(),
            "total_sales": total_sales or 0,
            "invoice_count": count_invoices or 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener las estadísticas de ventas: {e}")


# ============================================================
# 3 VENTAS POR RANGO DE TIEMPO — /api/dashboard/sales-by-category
# ============================================================
@router.get("/sales-by-category", response_model=Dict[str, Any])
def get_sales_by_category(
    session: SessionDep,
    range_type: str = Query(
        "mensual",
        description="Rango de tiempo: 'mensual', 'trimestral' o 'anual'"
    )
):
    """
    Devuelve las ventas agrupadas por categoría del menú (Platos Fuertes, Entradas, etc.)
    dentro del rango temporal seleccionado: mensual, trimestral o anual.
    """
    try:
        now = datetime.utcnow()

        # Determinar fecha inicial según el rango
        if range_type == "mensual":
            start_date = now.replace(day=1)
        elif range_type == "trimestral":
            month_start = ((now.month - 1) // 3) * 3 + 1
            start_date = now.replace(month=month_start, day=1)
        elif range_type == "anual":
            start_date = now.replace(month=1, day=1)
        else:
            raise HTTPException(
                status_code=400,
                detail="Rango inválido. Use: mensual, trimestral o anual."
            )

        # Consulta de ventas por categoría
        query = (
            select(Category.name.label("category_name"), func.sum(OrderItems.price_at_order * OrderItems.quantity).label("total_sales"), func.count(OrderItems.id).label("items_sold"))
            .join(MenuItem, MenuItem.id == OrderItems.id_menu_item)
            .join(Category, Category.id == MenuItem.id_category)
            .join(Invoice, Invoice.id_order == OrderItems.id_order)
            .where(Invoice.created_at >= start_date)
            .where(Invoice.deleted == False)
            .group_by(Category.id)
        )

        results = session.exec(query).all()

        # Transformar los resultados en lista de diccionarios
        sales_by_category = [
            {
                "category": row.category_name,
                "total_sales": float(row.total_sales or 0),
                "items_sold": int(row.items_sold or 0)
            }
            for row in results
        ]

        # Calcular el total global
        total_general = sum(item["total_sales"] for item in sales_by_category)

        return {
            "range": range_type,
            "start_date": start_date.isoformat(),
            "end_date": now.isoformat(),
            "total_general": total_general,
            "sales_by_category": sales_by_category
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener las ventas por categoría: {e}"
        )

# ============================================================
# 4 ÍTEMS MÁS VENDIDOS — /api/dashboard/popular-items
# ============================================================
@router.get("/popular-items", response_model=Dict[str, Any])
def get_popular_items(session: SessionDep, limit: int = Query(5, le=20)):
    """
    Retorna los ítems más vendidos según la cantidad total ordenada.
    """
    try:
        query = (
            select(
                MenuItem.name,
                func.sum(OrderItems.quantity). label("total_sold")
            )
            .join(OrderItems, MenuItem.id == OrderItems.id_menu_item)
            .group_by(MenuItem.name)
            .order_by(func.sum(OrderItems.quantity).desc())
            .limit(limit)
        )
        results = session.exec(query).all()

        return {
            "top_items": [
                {"item": row[0], "total_sold": int(row[1])} for row in results
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener los ítems más vendidos: {e}")


# ============================================================
# 5 CLIENTES FRECUENTES — /api/dashboard/top-clients
# ============================================================
@router.get("/top-clients", response_model=Dict[str, Any])
def get_top_clients(session: SessionDep, limit: int = Query(5, le=20)):
    """
    Retorna los clientes con más facturas generadas.
    """
    try:
        query = (
            select(Client.fullname, func.count(Invoice.id).label("invoice_count"))
            .join(Invoice, Client.id == Invoice.id_client)
            .group_by(Client.fullname)
            .order_by(func.count(Invoice.id).desc())
            .limit(limit)
        )
        results = session.exec(query).all()

        return {
            "top_clients": [
                {"client": row[0], "invoice_count": int(row[1])} for row in results
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener los clientes frecuentes: {e}")


# ============================================================
# 6 DESEMPEÑO DE PERSONAL — /api/dashboard/performance
# ============================================================
@router.get("/performance", response_model=Dict[str, Any])
def get_staff_performance(session: SessionDep):
    """
    Mide la productividad de meseros según las órdenes que han gestionado.
    Ahora incluye el nombre del mesero.
    """
    try:
        query = (
            select(
                Order.id_user_created.label("user_id"),
                func.count(Order.id).label("order_count"),
                func.sum(Order.total_value).label("total_sales")
            )
            .where(Order.id_user_created.isnot(None))
            .group_by(Order.id_user_created)
        )

        results = session.exec(query).all()

        performance = []
        for row in results:
            user_id, order_count, total_sales = row

            # Buscar el nombre del usuario (mesero)
            user = session.exec(
                select(User.name).where(User.id == user_id)
            ).first()

            waiter_name = user if user else "Desconocido"

            performance.append({
                "user_id": user_id,
                "waiter_name": waiter_name,
                "orders": int(order_count or 0),
                "sales": float(total_sales or 0)
            })

        return {"staff_performance": performance}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener el desempeño del personal: {e}"
        )
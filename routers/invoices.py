from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlmodel import select, col, func
from datetime import datetime
from typing import List, Optional
import os
from dotenv import load_dotenv

# Core
from core.database import SessionDep
from core.security import decode_token

# Modelos
from models.invoices import Invoice
from models.orders import Order
from models.tables import Table

# Schemas
from schemas.invoices_schema import (
    InvoiceRead,
    InvoiceCreate,
    InvoiceUpdate,
    InvoiceCreateConsolidated,
    InvoiceCountResponse,
    InvoiceAnnulment,
    InvoicePaymentUpdate
)

# Cargar variables de entorno
load_dotenv()

# === CONSTANTES DE ESTADOS (leer desde .env) ===
ID_STATUS_DELIVERED = int(os.getenv('ID_STATUS_DELIVERED', 6))
ID_STATUS_PENDING = int(os.getenv('ID_STATUS_PENDING', 15))
ID_STATUS_ANNULLED = int(os.getenv('ID_STATUS_ANNULLED', 12))
ID_STATUS_PAID = int(os.getenv('ID_STATUS_PAID', 13))
ID_STATUS_ORDER_PAID = int(os.getenv('ID_STATUS_ORDER_PAID', 13))
ID_STATUS_TABLE_OCCUPIED = int(os.getenv('ID_STATUS_TABLE_OCCUPIED', 3))
ID_STATUS_TABLE_AVAILABLE = int(os.getenv('ID_STATUS_TABLE_AVAILABLE', 4))

# === CONFIGURACIÓN DEL ROUTER ===
router = APIRouter(
    tags=["INVOICES"],
    prefix="/api/invoices",
    dependencies=[Depends(decode_token)]
)

# ==============================================================
# GET → Listado completo con filtros
# ==============================================================

@router.get("", response_model=List[InvoiceRead], status_code=status.HTTP_200_OK)
def list_invoices(
    session: SessionDep,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    id: Optional[int] = None,
    id_status: Optional[int] = None,
    id_client: Optional[int] = None,
    min_total: Optional[float] = None,
    max_total: Optional[float] = None,
    created_from: Optional[datetime] = None,
    created_to: Optional[datetime] = None,
    id_table: Optional[int] = None,
    id_waiter: Optional[int] = None,
    include_deleted: bool = False
):
    """Lista todas las facturas con filtros avanzados."""
    try:
        statement = select(Invoice)

        # Join con Order si se filtra por mesa o mesero
        if id_table or id_waiter:
            statement = statement.join(Order, Invoice.id_order == Order.id)
            if id_table:
                statement = statement.where(Order.id_table == id_table)
            if id_waiter:
                statement = statement.where(Order.id_user_created == id_waiter)

        # Filtros generales
        if not include_deleted:
            statement = statement.where(Invoice.deleted == False)
        if id:
            statement = statement.where(Invoice.id == id)
        if id_status:
            statement = statement.where(Invoice.id_status == id_status)
        if id_client:
            statement = statement.where(Invoice.id_client == id_client)
        if min_total:
            statement = statement.where(Invoice.total >= min_total)
        if max_total:
            statement = statement.where(Invoice.total <= max_total)
        if created_from:
            statement = statement.where(col(Invoice.created_at) >= created_from)
        if created_to:
            statement = statement.where(col(Invoice.created_at) <= created_to)

        statement = statement.limit(limit).offset(offset).order_by(Invoice.created_at.desc())
        return session.exec(statement).all()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar facturas: {e}")

# ==============================================================
# GET → Leer factura por ID
# ==============================================================

@router.get("/{invoice_id}", response_model=InvoiceRead)
def read_invoice(invoice_id: int, session: SessionDep):
    """Obtiene una factura específica."""
    invoice = session.get(Invoice, invoice_id)
    if not invoice or invoice.deleted:
        raise HTTPException(status_code=404, detail="Factura no encontrada o eliminada.")
    return invoice

# ==============================================================
# GET → Dashboard (Recuento de facturas)
# ==============================================================

@router.get("/dashboard/count", response_model=InvoiceCountResponse)
def get_invoice_counts(session: SessionDep):
    """Cuenta de facturas agrupadas por estado."""
    try:
        base = select(Invoice).where(Invoice.deleted == False)
        total_count = session.exec(select(func.count()).select_from(base.subquery())).one()

        counts = {
            "paid_count": session.exec(select(func.count()).select_from(base.where(Invoice.id_status == ID_STATUS_PAID).subquery())).one(),
            "annulled_count": session.exec(select(func.count()).select_from(base.where(Invoice.id_status == ID_STATUS_ANNULLED).subquery())).one(),
        }

        return InvoiceCountResponse(
            total_count=total_count,
            paid_count=counts["paid_count"],
            annulled_count=counts["annulled_count"],
            unpaid_count=0,
            draft_count=0,
            overdue_count=0
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al contar facturas: {e}")

# ==============================================================
# POST → Crear factura simple
# ==============================================================

@router.post("", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
def create_invoice(invoice_data: InvoiceCreate, session: SessionDep):
    """Crea una factura para una sola orden."""
    try:
        existing = session.exec(select(Invoice).where(Invoice.id_order == invoice_data.id_order).where(Invoice.deleted == False)).first()
        if existing:
            raise HTTPException(status_code=400, detail="Ya existe una factura activa para esta orden.")

        order = session.get(Order, invoice_data.id_order)
        if not order or order.deleted:
            raise HTTPException(status_code=404, detail="Orden no encontrada o eliminada.")

        invoice = Invoice(**invoice_data.model_dump(), created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        session.add(invoice)
        session.commit()
        session.refresh(invoice)
        return invoice

    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear factura: {e}")

# ==============================================================
# POST → Crear factura consolidada
# ==============================================================

@router.post("/consolidate-orders", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
def create_consolidated_invoice(invoice_data: InvoiceCreateConsolidated, session: SessionDep):
    """Crea una factura consolidada de varias órdenes."""
    try:
        orders = session.exec(select(Order).where(Order.id.in_(invoice_data.order_ids)).where(Order.deleted == False)).all()

        if len(orders) != len(invoice_data.order_ids):
            raise HTTPException(status_code=404, detail="Una o más órdenes no existen o están eliminadas.")

        for o in orders:
            if o.id_status != ID_STATUS_DELIVERED:
                raise HTTPException(status_code=400, detail=f"La orden {o.id} no está en estado Entregado.")

        total = sum(o.total_value for o in orders)
        paid = invoice_data.ammount_paid or 0
        returned = max(0, paid - total)

        invoice = Invoice(
            id_client=invoice_data.id_client,
            id_order=orders[0].id,
            id_payment_method=invoice_data.id_payment_method,
            id_status=ID_STATUS_PAID if paid >= total else ID_STATUS_PENDING,
            total=total,
            ammount_paid=paid,
            returned=returned,
            note=invoice_data.note,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        session.add(invoice)

        # Actualizar órdenes si factura pagada
        if invoice.id_status == ID_STATUS_PAID:
            for o in orders:
                o.id_status = ID_STATUS_ORDER_PAID
                o.updated_at = datetime.utcnow()
                session.add(o)

        session.commit()
        session.refresh(invoice)
        return invoice

    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error al consolidar facturas: {e}")

# ==============================================================
# PATCH → Actualizar factura
# ==============================================================

@router.patch("/{invoice_id}", response_model=InvoiceRead)
def update_invoice(invoice_id: int, invoice_data: InvoiceUpdate, session: SessionDep):
    """Actualiza los campos de una factura."""
    invoice = session.get(Invoice, invoice_id)
    if not invoice or invoice.deleted:
        raise HTTPException(status_code=404, detail="Factura no encontrada.")

    data = invoice_data.model_dump(exclude_unset=True)
    invoice.sqlmodel_update(data)
    invoice.updated_at = datetime.utcnow()
    session.add(invoice)
    session.commit()
    session.refresh(invoice)
    return invoice

# ==============================================================
# PATCH → Registrar pago o actualizar estado
# ==============================================================

@router.patch("/{invoice_id}/update", response_model=InvoiceRead)
def update_invoice_payment(invoice_id: int, payment_data: InvoicePaymentUpdate, session: SessionDep):
    """Registra pago, marca como pagada y libera la mesa."""
    invoice = session.get(Invoice, invoice_id)
    if not invoice or invoice.deleted:
        raise HTTPException(status_code=404, detail="Factura no encontrada.")

    if invoice.id_status in [ID_STATUS_PAID, ID_STATUS_ANNULLED]:
        raise HTTPException(status_code=400, detail="Factura ya pagada o anulada.")

    if payment_data.id_status == ID_STATUS_PAID:
        if not payment_data.ammount_paid or payment_data.ammount_paid < invoice.total:
            raise HTTPException(status_code=400, detail="Pago insuficiente.")

        invoice.id_status = ID_STATUS_PAID
        invoice.ammount_paid = payment_data.ammount_paid
        invoice.returned = payment_data.ammount_paid - invoice.total

        order = session.get(Order, invoice.id_order)
        if order:
            order.id_status = ID_STATUS_ORDER_PAID
            if order.id_table:
                table = session.get(Table, order.id_table)
                if table and table.id_status == ID_STATUS_TABLE_OCCUPIED:
                    table.id_status = ID_STATUS_TABLE_AVAILABLE
                    table.updated_at = datetime.utcnow()
                    session.add(table)
            session.add(order)

    invoice.updated_at = datetime.utcnow()
    session.add(invoice)
    session.commit()
    session.refresh(invoice)
    return invoice

# ==============================================================
# PATCH → Anular factura
# ==============================================================

@router.patch("/{invoice_id}/annul", response_model=InvoiceRead)
def annul_invoice(invoice_id: int, annulment_data: InvoiceAnnulment, session: SessionDep):
    """Anula una factura con soft delete."""
    invoice = session.get(Invoice, invoice_id)
    if not invoice or invoice.deleted:
        raise HTTPException(status_code=404, detail="Factura no encontrada.")
    if invoice.id_status == ID_STATUS_ANNULLED:
        raise HTTPException(status_code=400, detail="Factura ya anulada.")

    invoice.id_status = ID_STATUS_ANNULLED
    invoice.deleted = True
    invoice.deleted_on = datetime.utcnow()
    invoice.note = f"Anulada: {annulment_data.annulment_reason or 'Sin motivo'}"
    invoice.updated_at = datetime.utcnow()
    session.add(invoice)
    session.commit()
    session.refresh(invoice)
    return invoice

# ==============================================================
# DELETE → Soft delete
# ==============================================================

@router.delete("/{invoice_id}", response_model=dict)
def delete_invoice(invoice_id: int, session: SessionDep):
    """Elimina (soft delete) una factura."""
    invoice = session.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada.")
    if invoice.deleted:
        return {"message": "Factura ya eliminada."}

    invoice.deleted = True
    invoice.deleted_on = datetime.utcnow()
    invoice.updated_at = datetime.utcnow()
    session.add(invoice)
    session.commit()
    return {"message": f"Factura ID {invoice_id} eliminada exitosamente."}

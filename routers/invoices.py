from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy import Table
from sqlmodel import select, Session, func, col, join
from datetime import datetime
from typing import List, Optional

# Importa las dependencias del Core y Modelos (Asume que existen)
from core.database import SessionDep, get_session
from core.security import decode_token 

# Modelos (Asume que existen)
from models.invoices import Invoice 
from models.orders import Order 
# from models.status import Status # No es estrictamente necesario si solo usamos IDs

# Schemas (Asume que existen en schemas/invoices_schema.py)
from schemas.invoices_schema import (
    InvoiceRead, 
    InvoiceCreate, 
    InvoiceUpdate, 
    InvoiceCreateConsolidated,
    InvoiceCountResponse, 
    InvoiceAnnulment,
    InvoicePaymentUpdate  
)

#cargar variables de entorno
from dotenv import load_dotenv
import os
load_dotenv()

# --- IDs DE ESTADO REQUERIDOS ---
ID_STATUS_DELIVERED = int(os.getenv('ID_STATUS_DELIVERED'))    # <-- ID del estado 'Entregado' en la tabla STATUS (AJUSTA ESTE VALOR)
ID_STATUS_PENDING = int(os.getenv('ID_STATUS_PENDING'))     # <-- ID del estado 'Pendiente' de Factura
ID_STATUS_ANNULLED =    int(os.getenv('ID_STATUS_ANNULLED')) # <-- ID del estado 'Anulada' de Factura
ID_STATUS_PAID =    int(os.getenv('ID_STATUS_PAID'))        # <-- ID del estado 'Pagada'
ID_STATUS_ORDER_PAID = int(os.getenv('ID_STATUS_ORDER_PAID'))  # <-- El estado de la orden al ser facturada/pagada (Puede ser igual a ID_STATUS_PAID)
ID_STATUS_TABLE_OCCUPIED = int(os.getenv('ID_STATUS_TABLE_OCCUPIED'))  # Mesa Ocupada (ID que viene de tu DB)
ID_STATUS_TABLE_AVAILABLE = int(os.getenv('ID_STATUS_TABLE_AVAILABLE')) # Mesa Disponible (ID

# Configuración del Router
router = APIRouter(tags=["INVOICES"], prefix='/api/invoices', dependencies=[Depends(decode_token)]) 


# ======================================================================
# RUTAS DE LECTURA (GET)
# ======================================================================

# 1. GET → Vista Maestra con TODOS los Filtros (Administración)
@router.get("", response_model=List[InvoiceRead], status_code=status.HTTP_200_OK)
def list_master_invoices(
    session: SessionDep,
    # Filtros de Paginación
    limit: int = Query(20, ge=1, le=100, description="Límite de resultados"),
    offset: int = Query(0, ge=0, description="Desplazamiento"),
    # Filtros por Campos
    id: Optional[int] = Query(None, description="Filtrar por ID de Factura"),
    id_status: Optional[int] = Query(None, description="Filtrar por ID de Estado"),
    id_client: Optional[int] = Query(None, description="Filtrar por ID de Cliente"),
    # Filtros por Rango de Monto
    min_total: Optional[float] = Query(None, ge=0, description="Monto total mínimo"),
    max_total: Optional[float] = Query(None, ge=0, description="Monto total máximo"),
    # Filtros de Fecha
    created_from: Optional[datetime] = Query(None, description="Desde fecha de creación"),
    created_to: Optional[datetime] = Query(None, description="Hasta fecha de creación"),
    # Filtros Relacionales (Requieren JOIN con Order)
    id_table: Optional[int] = Query(None, description="Filtrar por ID de Mesa (vía Orden)"),
    id_waiter: Optional[int] = Query(None, description="Filtrar por ID de Mesero/Creador de la Orden"),
    # Parámetro de Soft Delete
    include_deleted: bool = Query(False, description="Incluir facturas marcadas como eliminadas/anuladas"),
):
    """
    Obtiene una lista completa de facturas con filtros avanzados, paginación, 
    y join a la Orden para filtros de Mesa/Mesero.
    """
    try:
        statement = select(Invoice)
        
        # 1. Inicialización del JOIN si se requiere filtro relacional
        if id_table is not None or id_waiter is not None:
            # JOIN implícito con la Orden
            statement = select(Invoice).join(Order, Invoice.id_order == Order.id)
            
            if id_table is not None:
                statement = statement.where(Order.id_table == id_table)
            if id_waiter is not None:
                # Asumo que el mesero es Order.id_user_created
                statement = statement.where(Order.id_user_created == id_waiter)
        
        # 2. Filtro Soft Delete
        if not include_deleted:
            statement = statement.where(Invoice.deleted == False)

        # 3. Aplicación de Filtros Simples y Rango
        if id is not None:
            statement = statement.where(Invoice.id == id)
        if id_status is not None:
            statement = statement.where(Invoice.id_status == id_status)
        if id_client is not None:
            statement = statement.where(Invoice.id_client == id_client)
        if min_total is not None:
            statement = statement.where(Invoice.total >= min_total)
        if max_total is not None:
            statement = statement.where(Invoice.total <= max_total)
        if created_from:
            statement = statement.where(col(Invoice.created_at) >= created_from)
        if created_to:
            statement = statement.where(col(Invoice.created_at) <= created_to)

        # 4. Paginación y Ejecución
        statement = statement.limit(limit).offset(offset).order_by(Invoice.created_at.desc())
        invoices = session.exec(statement).all()
        
        return invoices
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al listar facturas con filtros: {str(e)}")

# 3. GET → Recuento para Dashboard
@router.get("/dashboard/count-invoices", response_model=InvoiceCountResponse, status_code=status.HTTP_200_OK)
def get_invoice_counts(
    session: SessionDep,
    created_from: Optional[datetime] = Query(None),
    created_to: Optional[datetime] = Query(None)
):
    """Proporciona recuentos de facturas por estado para el dashboard, con filtros de fecha."""
    base_query = select(Invoice).where(Invoice.deleted == False)

    if created_from:
        base_query = base_query.where(col(Invoice.created_at) >= created_from)
    if created_to:
        base_query = base_query.where(col(Invoice.created_at) <= created_to)

    try:
        total_count = session.exec(select(func.count()).select_from(base_query.subquery())).one()
        
        # Filtros específicos de estado
        counts = {
            "paid_count": session.exec(select(func.count()).select_from(base_query.where(Invoice.id_status == ID_STATUS_PAID).subquery())).one(), 
            "annulled_count": session.exec(select(func.count()).select_from(base_query.where(Invoice.id_status == ID_STATUS_ANNULLED).subquery())).one(),
            # Añade aquí los otros contadores (unpaid, draft, overdue) usando sus IDs de estado.
        }

        return InvoiceCountResponse(
            total_count=total_count,
            paid_count=counts["paid_count"],
            annulled_count=counts["annulled_count"],
            unpaid_count=0, draft_count=0, overdue_count=0 # Placeholder si no se definen los IDs
        )

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al obtener el recuento: {str(e)}")


# 2. GET → Leer Factura Específica (Original)
@router.get("/{invoice_id}", response_model=InvoiceRead)
def read_invoice(invoice_id: int, session: SessionDep):
    """Obtiene una factura específica por su ID (si no está eliminada)."""
    try:
        invoice_db = session.get(Invoice, invoice_id)
        
        if not invoice_db or invoice_db.deleted is True:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Factura no encontrada o eliminada.")
        return invoice_db
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al leer la factura: {str(e)}")

# 3. GET → Recuento para Dashboard
@router.get("/dashboard-count", response_model=InvoiceCountResponse, status_code=status.HTTP_200_OK)
def get_invoice_counts(
    session: SessionDep,
    created_from: Optional[datetime] = Query(None),
    created_to: Optional[datetime] = Query(None)
):
    """Proporciona recuentos de facturas por estado para el dashboard, con filtros de fecha."""
    base_query = select(Invoice).where(Invoice.deleted == False)

    if created_from:
        base_query = base_query.where(col(Invoice.created_at) >= created_from)
    if created_to:
        base_query = base_query.where(col(Invoice.created_at) <= created_to)

    try:
        total_count = session.exec(select(func.count()).select_from(base_query.subquery())).one()
        
        # Filtros específicos de estado
        counts = {
            "paid_count": session.exec(select(func.count()).select_from(base_query.where(Invoice.id_status == ID_STATUS_PAID).subquery())).one(), 
            "annulled_count": session.exec(select(func.count()).select_from(base_query.where(Invoice.id_status == ID_STATUS_ANNULLED).subquery())).one(),
            # Añade aquí los otros contadores (unpaid, draft, overdue) usando sus IDs de estado.
        }

        return InvoiceCountResponse(
            total_count=total_count,
            paid_count=counts["paid_count"],
            annulled_count=counts["annulled_count"],
            unpaid_count=0, draft_count=0, overdue_count=0 # Placeholder si no se definen los IDs
        )

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al obtener el recuento: {str(e)}")


# ======================================================================
# RUTAS DE CREACIÓN (POST)
# ======================================================================

# 4. POST → Crear Factura (Para una Sola Orden - Uso Legacy/API)
@router.post("", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
def create_invoice(invoice_data: InvoiceCreate, session: SessionDep):
    """Crea una nueva factura para una *sola* orden (Uso Legacy/Admin)."""
    try:
        existing_invoice = session.exec(select(Invoice).where(Invoice.id_order == invoice_data.id_order).where(Invoice.deleted == False)).first()
        if existing_invoice:
            raise HTTPException(status_code=400, detail=f"Ya existe una factura activa para la Orden ID: {invoice_data.id_order}.")
        
        order_db = session.get(Order, invoice_data.id_order)
        if not order_db or order_db.deleted is True:
            raise HTTPException(status_code=404, detail=f"La Orden ID: {invoice_data.id_order} no existe o está eliminada.")

        invoice_db = Invoice.model_validate(invoice_data.model_dump())
        invoice_db.created_at = datetime.utcnow()
        invoice_db.updated_at = datetime.utcnow()

        session.add(invoice_db)
        session.commit()
        session.refresh(invoice_db)
        
        return invoice_db

    except HTTPException:
        raise
    except Exception as e:
        session.rollback() 
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al crear la factura: {str(e)}")

# 5. POST → Crear Factura CONSOLIDADA (Opción 1: TPV/POS)
@router.post("/api/invoices/consolidate-orders", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
def create_consolidated_invoice(
    invoice_data: InvoiceCreateConsolidated, 
    session: SessionDep
):
    """
    Crea una única factura consolidada a partir de IDs de órdenes.
    Requiere que TODAS las órdenes a facturar estén en estado 'Entregado' (ID 6).
    La factura se crea en estado Pendiente (ID 15) por defecto.
    """
    order_ids = invoice_data.order_ids
    
    try:
        # 1. Obtener Órdenes, Validar Existencia
        orders = session.exec(select(Order).where(Order.id.in_(order_ids)).where(Order.deleted == False)).all()
        
        if len(orders) != len(order_ids):
            missing_ids = set(order_ids) - {o.id for o in orders}
            raise HTTPException(status_code=404, detail=f"Órdenes no encontradas o eliminadas: {list(missing_ids)}")
        
        # 🔴 VALIDACIÓN DE ESTADO: Todas las órdenes deben estar en estado ENTREGADO
        for order in orders:
            if order.id_status != ID_STATUS_DELIVERED:
                # Se obtiene el nombre del estado actual para un mejor mensaje de error
                status_name = session.exec(select(status.name).where(status.id == order.id_status)).first()
                status_name = status_name if status_name else "Desconocido"
                
                raise HTTPException(
                    status_code=400, 
                    detail=f"La Orden ID: {order.id} no ha sido Entregada y tiene estado '{status_name}'. Debe estar en estado Entregado para facturar."
                )
        
        # 2. Consolidar Cálculos
        total_due_amount = sum(order.total_value for order in orders)
        final_total = total_due_amount
        ammount_paid = invoice_data.ammount_paid if invoice_data.ammount_paid is not None else 0.00
        returned_amount = max(0, ammount_paid - final_total) # Evita números negativos en returned

        # 3. Determinar el Estado Inicial de la Factura
        initial_status_id = ID_STATUS_PENDING # Por defecto, la factura se crea Pendiente

        # Si hay un monto de pago y es suficiente, la factura se crea Pagada inmediatamente
        if ammount_paid > 0 and ammount_paid >= final_total:
             initial_status_id = ID_STATUS_PAID
        
        # 4. Crear el Objeto Factura
        final_order_id = orders[0].id # Usamos el ID de la primera orden como referencia principal
        now = datetime.utcnow()
        
        invoice_db = Invoice(
            id_client=invoice_data.id_client,
            id_order=final_order_id, 
            id_payment_method=invoice_data.id_payment_method,
            id_status=invoice_data.id_status if invoice_data.id_status else initial_status_id, 
            returned=returned_amount,
            ammount_paid=ammount_paid,
            total=final_total,
            note=invoice_data.note,
            created_at=now, updated_at=now
        )
        
        session.add(invoice_db)
        session.flush() # Para obtener el ID de la factura si es necesario más adelante

        # 5. Actualizar estado de TODAS las órdenes subyacentes
        # SOLO si la factura se ha marcado como PAGADA inmediatamente
        if initial_status_id == ID_STATUS_PAID:
            for order in orders:
                order.id_status = ID_STATUS_ORDER_PAID # 13
                order.updated_at = now
                session.add(order)

        session.commit()
        session.refresh(invoice_db)
        
        return invoice_db

    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al generar la factura consolidada: {str(e)}")


# ======================================================================
# RUTAS DE ACTUALIZACIÓN (PATCH)
# ======================================================================

# 6. PATCH → Actualizar Campos de Factura (Original)
@router.patch("/{invoice_id}", response_model=InvoiceRead)
def update_invoice(invoice_id: int, invoice_data: InvoiceUpdate, session: SessionDep):
    """Actualiza campos de una factura existente (si no está eliminada)."""
    try:
        invoice_db = session.get(Invoice, invoice_id)

        if not invoice_db or invoice_db.deleted is True:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Factura no encontrada o eliminada.")
        
        data_to_update = invoice_data.model_dump(exclude_unset=True)
        
        if "id_order" in data_to_update and data_to_update["id_order"] != invoice_db.id_order:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se permite cambiar la orden asociada a una factura existente.")

        invoice_db.sqlmodel_update(data_to_update)
        invoice_db.updated_at = datetime.utcnow()
        
        session.add(invoice_db)
        session.commit()
        session.refresh(invoice_db)
        return invoice_db
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al actualizar la factura: {str(e)}")

# 7. PATCH → Anular Factura
@router.patch("/{invoice_id}/annul", response_model=InvoiceRead, status_code=status.HTTP_200_OK)
def annul_invoice(invoice_id: int, annulment_data: InvoiceAnnulment, session: SessionDep):
    """Anula una factura aplicando Soft Delete (deleted=True) y estado Anulada (ID 12)."""
    try:
        invoice_db = session.get(Invoice, invoice_id)

        if not invoice_db or invoice_db.deleted is True:
            raise HTTPException(status_code=404, detail="Factura no encontrada o ya eliminada.")

        if invoice_db.id_status == ID_STATUS_ANNULLED:
            raise HTTPException(status_code=400, detail="La factura ya se encuentra anulada.")

        # Aplicar anulación
        invoice_db.id_status = ID_STATUS_ANNULLED
        invoice_db.deleted = True              
        invoice_db.deleted_on = datetime.utcnow()
        invoice_db.updated_at = datetime.utcnow()
        
        if annulment_data.annulment_reason:
            invoice_db.note = f"Anulada: {annulment_data.annulment_reason}"
        
        session.add(invoice_db)
        session.commit()
        session.refresh(invoice_db)
        return invoice_db
        
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al anular la factura: {str(e)}")


# ======================================================================
# RUTAS DE ELIMINACIÓN (DELETE)
# ======================================================================

# 8. DELETE → Eliminación Suave (Original)
@router.delete("/{invoice_id}", status_code=status.HTTP_200_OK, response_model=dict)
def delete_invoice(invoice_id: int, session: SessionDep):
    """Realiza la 'Eliminación Suave' de una factura."""
    try:
        invoice_db = session.get(Invoice, invoice_id)

        if not invoice_db:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Factura no encontrada.")
        
        if invoice_db.deleted is True:
            return {"message": f"La Factura (ID: {invoice_id}) ya estaba marcada como eliminada."}

        current_time = datetime.utcnow()

        # Aplicar Soft Delete
        invoice_db.deleted = True
        invoice_db.deleted_on = current_time
        invoice_db.updated_at = current_time
        
        session.add(invoice_db)
        session.commit()
        
        return {"message": f"Factura (ID: {invoice_id}) eliminada (Soft Delete) exitosamente."}
    
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al eliminar la factura: {str(e)}")
    
# 8. PATCH → Registrar Pago o Cambiar Estado (TPV) - LÓGICA DE LIBERACIÓN DE MESA AÑADIDA
@router.patch("/{invoice_id}/update", response_model=InvoiceRead)
def update_invoice_payment_status(
    invoice_id: int, 
    payment_data: InvoicePaymentUpdate, 
    session: SessionDep
):
    """
    Registra el pago de una factura (PENDING -> PAID) o cambia su estado.
    Cuando el estado final es PAGADA (ID 13), la mesa asociada a la orden se cambia a DISPONIBLE (ID 4).
    """
    try:
        # --- 1. Obtener Factura ---
        invoice_db = session.get(Invoice, invoice_id)

        if not invoice_db or invoice_db.deleted is True:
            raise HTTPException(status_code=404, detail="Factura no encontrada o eliminada.")
        
        # --- 2. Restricción de Modificación ---
        # NO permite modificar si ya estaba pagada, anulada o si el nuevo estado es diferente
        if invoice_db.id_status in [ID_STATUS_PAID, ID_STATUS_ANNULLED]:
             raise HTTPException(status_code=400, detail="No se puede modificar una factura ya Pagada o Anulada.")
        
        # --- 3. Aplicar Actualizaciones (Generales) ---
        data_to_update = payment_data.model_dump(exclude_unset=True)
        invoice_db.sqlmodel_update(data_to_update)
        
        
        # --- 4. Lógica de Pago (Si el nuevo estado es PAGADA) ---
        if payment_data.id_status == ID_STATUS_PAID:
            
            final_total = invoice_db.total
            ammount_paid = payment_data.ammount_paid if payment_data.ammount_paid is not None else invoice_db.ammount_paid
            
            if ammount_paid is None or ammount_paid < final_total:
                 raise HTTPException(status_code=400, detail=f"Monto de pago insuficiente para marcar como PAGADA. Requiere: {final_total:.2f}")

            # a. Actualizar campos de pago de la factura
            invoice_db.ammount_paid = ammount_paid
            invoice_db.returned = ammount_paid - final_total
            invoice_db.id_status = ID_STATUS_PAID
            
            # b. Actualizar la ORDEN subyacente a Pagada (ID 13)
            order_db = session.get(Order, invoice_db.id_order)
            if order_db:
                order_db.id_status = ID_STATUS_PAID
                order_db.updated_at = datetime.utcnow()
                session.add(order_db)
                
                # c. 🚀 LIBERAR LA MESA (Mesa Ocupada ID 3 -> Disponible ID 4)
                if order_db.id_table:
                    table_db = session.get(Table, order_db.id_table)
                    
                    if table_db and table_db.id_status == ID_STATUS_TABLE_OCCUPIED:
                        table_db.id_status = ID_STATUS_TABLE_AVAILABLE # ID 4
                        table_db.updated_at = datetime.utcnow()
                        session.add(table_db)

        # --- 5. Commit ---
        invoice_db.updated_at = datetime.utcnow()
        session.add(invoice_db)
        session.commit()
        session.refresh(invoice_db)
        return invoice_db
    
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error al actualizar el pago/estado: {str(e)}")
from fastapi import APIRouter, Depends, status, HTTPException
from sqlmodel import select
from datetime import datetime
from typing import List

# Importa las dependencias del Core
from core.database import SessionDep
from core.security import decode_token 

from models.invoices import Invoice 
from models.orders import Order # Necesario para validación
from schemas.invoices_schema import InvoiceCreate, InvoiceRead, InvoiceUpdate 

# Configuración del Router
# Uso 'INVOICES' como tag para agrupar en la documentación de la API (Swagger/Redoc)
router = APIRouter(tags=["INVOICES"]) 


# Rutas para lectura (GET)
@router.get("/api/invoices", response_model=List[InvoiceRead], dependencies=[Depends(decode_token)])
def list_invoices(session: SessionDep):
    """
    Obtiene una lista de todas las facturas **activas** (no eliminadas).
    """
    try:
        # Filtra por facturas donde deleted_at es NULL (no eliminadas)
        statement = select(Invoice).where(Invoice.deleted_at == None)
        return session.exec(statement).all()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar las facturas: {str(e)}",
        )

@router.get("/api/invoices/{invoice_id}", response_model=InvoiceRead, dependencies=[Depends(decode_token)])
def read_invoice(invoice_id: int, session: SessionDep):
    """Obtiene una factura específica por su ID."""
    try:
        invoice_db = session.get(Invoice, invoice_id)
        
        # Validación de existencia y de eliminación suave
        if not invoice_db or invoice_db.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Factura no encontrada o eliminada."
            )
        return invoice_db
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al leer la factura: {str(e)}",
        )

# Ruta para creacion (CREATE)
@router.post("/api/invoices", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(decode_token)])
def create_invoice(invoice_data: InvoiceCreate, session: SessionDep):
    """Crea una nueva factura para una orden."""
    try:
        # Validación de Unicidad (Una Factura por Orden)
        existing_invoice = session.exec(
            select(Invoice)
            .where(Invoice.id_order == invoice_data.id_order)
            .where(Invoice.deleted_at == None)
        ).first()
        if existing_invoice:
            raise HTTPException(
               status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ya existe una factura activa para la Orden ID: {invoice_data.id_order}." 
            )
        
        # Validación de Orden Padre (Debe existir y no estar eliminada)
        order_db = session.get(Order, invoice_data.id_order)
        if not order_db or order_db.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"La Orden ID: {invoice_data.id_order} no existe o está eliminada."
            )

        # Creación de la Factura
        invoice_db = Invoice.model_validate(invoice_data.model_dump())
        invoice_db.created_at = datetime.utcnow()
        invoice_db.updated_at = datetime.utcnow()

        session.add(invoice_db)
        session.commit()
        session.refresh(invoice_db)
        
        # Opcional: Actualizar el estado de la Orden a 'Facturada' si es necesario
        # order_db.id_status = ID_STATUS_FACTURADA 
        # session.add(order_db)
        # session.commit()
        
        return invoice_db

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback() 
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear la factura: {str(e)}",
        )

# Rutas para actualizar (PATCH)
@router.patch("/api/invoices/{invoice_id}", response_model=InvoiceRead, dependencies=[Depends(decode_token)])
def update_invoice(invoice_id: int, invoice_data: InvoiceUpdate, session: SessionDep):
    """Actualiza campos de una factura existente."""
    try:
        invoice_db = session.get(Invoice, invoice_id)

        # Validación: La factura debe existir y no estar eliminada
        if not invoice_db or invoice_db.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Factura no encontrada o eliminada."
            )
        
        data_to_update = invoice_data.model_dump(exclude_unset=True)
        
        # Validar si se intenta cambiar la Orden (id_order)
        if "id_order" in data_to_update and data_to_update["id_order"] != invoice_db.id_order:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="No se permite cambiar la orden asociada a una factura existente."
            )

        # Aplicar actualización y actualizar timestamp
        invoice_db.sqlmodel_update(data_to_update)
        invoice_db.updated_at = datetime.utcnow()
        
        session.add(invoice_db)
        session.commit()
        session.refresh(invoice_db)
        return invoice_db
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar la factura: {str(e)}",
        )

# Ruta para eliminacion (DELETE - Soft Delete)
@router.delete("/api/invoices/{invoice_id}", status_code=status.HTTP_200_OK, response_model=dict, dependencies=[Depends(decode_token)])
def delete_invoice(invoice_id: int, session: SessionDep):
    """Realiza la 'Eliminación Suave' de una factura."""
    try:
        invoice_db = session.get(Invoice, invoice_id)

        if not invoice_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Factura no encontrada."
            )
        
        if invoice_db.deleted_at is not None:
            return {"message": f"La Factura (ID: {invoice_id}) ya estaba marcada como eliminada."}

        current_time = datetime.utcnow()

        # Aplicar Soft Delete
        invoice_db.deleted_at = current_time
        invoice_db.updated_at = current_time
        session.add(invoice_db)
        session.commit()
        
        return {"message": f"Factura (ID: {invoice_id}) eliminada (Soft Delete) exitosamente."}
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar la factura: {str(e)}",
        )
from fastapi import APIRouter, Depends, status, HTTPException
from sqlmodel import select
from datetime import datetime
from typing import List

# Importa las dependencias del Core
from core.database import SessionDep
from core.security import decode_token 

from models.payment_method import PaymentMethod
from schemas.payment_method_schema import PaymentMethodCreate, PaymentMethodRead, PaymentMethodUpdate 

# Configuración del Router
# Uso 'PAYMENT METHODS' como tag para agrupar en la documentación de la API (Swagger/Redoc)
router = APIRouter(tags=["PAYMENT METHODS"]) 


# Rutas para lectura (GET)
@router.get("/api/payment_methods", response_model=List[PaymentMethodRead], dependencies=[Depends(decode_token)])
def list_payment_methods(session: SessionDep):
    """
    Obtiene una lista de todos los métodos de pago **activos** (no eliminados).
    """
    try:
        # Filtra por métodos donde deleted_at es NULL (no eliminados)
        statement = select(PaymentMethod).where(PaymentMethod.deleted_at == None)
        return session.exec(statement).all()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar los métodos de pago: {str(e)}",
        )

@router.get("/api/payment_methods/{method_id}", response_model=PaymentMethodRead, dependencies=[Depends(decode_token)])
def read_payment_method(method_id: int, session: SessionDep):
    """Obtiene un método de pago específico por su ID."""
    try:
        method_db = session.get(PaymentMethod, method_id)
        
        # Validación de existencia y de eliminación suave
        if not method_db or method_db.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Método de pago no encontrado o eliminado."
            )
        return method_db
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al leer el método de pago: {str(e)}",
        )

# Ruta para creacion (CREATE)
@router.post("/api/payment_methods", response_model=PaymentMethodRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(decode_token)])
def create_payment_method(method_data: PaymentMethodCreate, session: SessionDep):
    """Crea un nuevo método de pago, validando que el nombre sea único."""
    try:
        # Validación de Unicidad por nombre (solo para registros activos)
        existing_method = session.exec(
            select(PaymentMethod)
            .where(PaymentMethod.name == method_data.name)
            .where(PaymentMethod.deleted_at == None)
        ).first()
        if existing_method:
            raise HTTPException(
               status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ya existe un método de pago activo con el nombre: '{method_data.name}'." 
            )

        # Creación del Método de Pago
        method_db = PaymentMethod.model_validate(method_data.model_dump())
        method_db.created_at = datetime.utcnow()
        method_db.updated_at = datetime.utcnow()

        session.add(method_db)
        session.commit()
        session.refresh(method_db)
        
        return method_db

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback() 
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear el método de pago: {str(e)}",
        )

# Rutas para actualizar (PATCH)
@router.patch("/api/payment_methods/{method_id}", response_model=PaymentMethodRead, dependencies=[Depends(decode_token)])
def update_payment_method(method_id: int, method_data: PaymentMethodUpdate, session: SessionDep):
    """Actualiza el nombre del método de pago, manteniendo la unicidad."""
    try:
        method_db = session.get(PaymentMethod, method_id)

        # Validación: El método debe existir y no estar eliminado
        if not method_db or method_db.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Método de pago no encontrado o eliminado."
            )
        
        data_to_update = method_data.model_dump(exclude_unset=True)
        
        # Validación de unicidad si se intenta cambiar el nombre
        if "name" in data_to_update and data_to_update["name"] != method_db.name:
            existing_method = session.exec(
                select(PaymentMethod)
                .where(PaymentMethod.name == data_to_update["name"])
                .where(PaymentMethod.deleted_at == None)
            ).first()
            
            # Si el nombre existe Y no pertenece al método que estamos actualizando
            if existing_method and existing_method.id != method_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ya existe un método de pago activo con el nombre: '{data_to_update['name']}'."
                )

        # Aplicar actualización y actualizar timestamp
        method_db.sqlmodel_update(data_to_update)
        method_db.updated_at = datetime.utcnow()
        
        session.add(method_db)
        session.commit()
        session.refresh(method_db)
        return method_db
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar el método de pago: {str(e)}",
        )

# Ruta para eliminacion (DELETE - Soft Delete)
@router.delete("/api/payment_methods/{method_id}", status_code=status.HTTP_200_OK, response_model=dict, dependencies=[Depends(decode_token)])
def delete_payment_method(method_id: int, session: SessionDep):
    """Realiza la 'Eliminación Suave' de un método de pago."""
    try:
        method_db = session.get(PaymentMethod, method_id)

        if not method_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Método de pago no encontrado."
            )
        
        if method_db.deleted_at is not None:
            return {"message": f"El Método de Pago (ID: {method_id}) ya estaba marcado como eliminado."}

        current_time = datetime.utcnow()

        # Aplicar Soft Delete
        method_db.deleted_at = current_time
        method_db.updated_at = current_time
        session.add(method_db)
        session.commit()
        
        return {"message": f"Método de Pago (ID: {method_id}) eliminado (Soft Delete) exitosamente."}
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar el método de pago: {str(e)}",
        )
from fastapi import APIRouter, Depends, status, HTTPException
from sqlmodel import select
from datetime import datetime
from typing import List

# Importa las dependencias del Core
from core.database import SessionDep
from core.security import decode_token 

from models.payment_method import PaymentMethod # Asume que ahora tiene 'deleted' y 'deleted_on'
from schemas.payment_method_schema import PaymentMethodCreate, PaymentMethodRead, PaymentMethodUpdate 

# Configuración del Router
router = APIRouter(
    prefix="/api/payment_methods", 
    tags=["PAYMENT METHODS"], 
    dependencies=[Depends(decode_token)]
) 

# --- RUTAS DE LECTURA (GET) ---

@router.get("", response_model=List[PaymentMethodRead]) # Ruta: /api/payment_methods
def list_payment_methods(session: SessionDep):
    """
    Obtiene una lista de todos los métodos de pago **activos** (deleted=False).
    """
    try:
        # >>> CAMBIO 1: Filtra por 'deleted == False'
        statement = select(PaymentMethod).where(PaymentMethod.deleted == False)
        return session.exec(statement).all()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar los métodos de pago: {str(e)}",
        )

@router.get("/{method_id}", response_model=PaymentMethodRead) # Ruta: /api/payment_methods/{method_id}
def read_payment_method(method_id: int, session: SessionDep):
    """Obtiene un método de pago específico por su ID. Solo devuelve métodos activos."""
    try:
        method_db = session.get(PaymentMethod, method_id)
        
        # >>> CAMBIO 2: Validación con 'deleted is True'
        if not method_db or method_db.deleted is True:
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

# --- RUTA PARA CREACIÓN (POST) ---

@router.post("", response_model=PaymentMethodRead, status_code=status.HTTP_201_CREATED) # Ruta: /api/payment_methods
def create_payment_method(method_data: PaymentMethodCreate, session: SessionDep):
    """Crea un nuevo método de pago, validando que el nombre sea único entre los activos."""
    try:
        # Validación de Unicidad por nombre (solo para registros activos)
        # >>> CAMBIO 3: Filtra por 'deleted == False'
        existing_method = session.exec(
            select(PaymentMethod)
            .where(PaymentMethod.name == method_data.name)
            .where(PaymentMethod.deleted == False)
        ).first()
        if existing_method:
            raise HTTPException(
               status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ya existe un método de pago activo con el nombre: '{method_data.name}'." 
            )

        # Creación del Método de Pago
        method_db = PaymentMethod.model_validate(method_data.model_dump())
        method_db.created_at = datetime.utcnow()
        method_db.updated_at = datetime.utcnow()
        # 'deleted' y 'deleted_on' se establecen por defecto (False y None)

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

# --- RUTA PARA ACTUALIZACIÓN (PATCH) ---

@router.patch("/{method_id}", response_model=PaymentMethodRead) # Ruta: /api/payment_methods/{method_id}
def update_payment_method(method_id: int, method_data: PaymentMethodUpdate, session: SessionDep):
    """Actualiza el nombre del método de pago, manteniendo la unicidad."""
    try:
        method_db = session.get(PaymentMethod, method_id)

        # >>> CAMBIO 4: Validación con 'deleted is True'
        if not method_db or method_db.deleted is True:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Método de pago no encontrado o eliminado."
            )
        
        data_to_update = method_data.model_dump(exclude_unset=True)
        
        # Validación de unicidad si se intenta cambiar el nombre
        if "name" in data_to_update and data_to_update["name"] != method_db.name:
            # >>> CAMBIO 5: Filtra por 'deleted == False'
            existing_method = session.exec(
                select(PaymentMethod)
                .where(PaymentMethod.name == data_to_update["name"])
                .where(PaymentMethod.deleted == False)
            ).first()
            
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

# --- RUTA PARA ELIMINACIÓN SUAVE (DELETE) ---

@router.delete("/{method_id}", status_code=status.HTTP_200_OK, response_model=dict) # Ruta: /api/payment_methods/{method_id}
def soft_delete_payment_method(method_id: int, session: SessionDep):
    """Realiza la 'Eliminación Suave' de un método de pago, marcando 'deleted=True'."""
    try:
        method_db = session.get(PaymentMethod, method_id)

        if not method_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Método de pago no encontrado."
            )
        
        # >>> CAMBIO 6: Usar 'deleted is True'
        if method_db.deleted is True:
            return {"message": f"El Método de Pago (ID: {method_id}) ya estaba marcado como eliminado."}

        current_time = datetime.utcnow()

        # Aplicar Soft Delete
        # >>> CAMBIO 7: Asignar deleted=True y deleted_on
        method_db.deleted = True
        method_db.deleted_on = current_time
        method_db.updated_at = current_time
        session.add(method_db)
        session.commit()
        
        return {"message": f"Método de Pago (ID: {method_id}) eliminado (Soft Delete) exitosamente el {current_time.isoformat()}."}
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar el método de pago: {str(e)}",
        )

# --- RUTA PARA RESTAURACIÓN (PATCH /restore) ---

@router.patch("/{method_id}/restore", response_model=PaymentMethodRead) # Ruta: /api/payment_methods/{method_id}/restore
def restore_deleted_payment_method(method_id: int, session: SessionDep):
    """
    Restaura un método de pago previamente eliminado (Soft Delete), 
    cambiando 'deleted' a False y limpiando 'deleted_on'.
    """
    try:
        method_db = session.get(PaymentMethod, method_id)

        if not method_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Método de pago no encontrado."
            )
        
        # Solo permite la restauración si está actualmente eliminado
        if method_db.deleted is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="El método de pago no está eliminado y no puede ser restaurado."
            )

        # Validación de unicidad: Verificar si el nombre está ocupado por otro método activo
        existing_method = session.exec(
            select(PaymentMethod)
            .where(PaymentMethod.name == method_db.name)
            .where(PaymentMethod.deleted == False)
        ).first()

        if existing_method:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail=f"Conflicto: No se puede restaurar. El nombre '{method_db.name}' ya está en uso por otro método de pago activo (ID: {existing_method.id})."
            )

        current_time = datetime.utcnow()

        # Restaurar el método
        method_db.deleted = False
        method_db.deleted_on = None  # Limpia la marca de tiempo de eliminación
        method_db.updated_at = current_time 

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
            detail=f"Error al restaurar el método de pago: {str(e)}",
        )
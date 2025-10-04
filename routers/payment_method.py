from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlmodel import select, func
from datetime import datetime, timezone
from typing import List, Optional

# Importa las dependencias del Core
from core.database import SessionDep
from core.security import decode_token 

from models.payment_method import PaymentMethod 
from schemas.payment_method_schema import PaymentMethodCreate, PaymentMethodRead, PaymentMethodUpdate, PaymentMethodListResponse # Asegúrate de crear PaymentMethodListResponse

# Configuración del Router
router = APIRouter(
    prefix="/api/payment_methods", 
    tags=["PAYMENT METHODS"], 
    dependencies=[Depends(decode_token)]
) 

# ======================================================================
# --- RUTA PRINCIPAL DE LECTURA (GET /) CON PAGINACIÓN Y FILTROS ---
# ======================================================================

@router.get(
    "", 
    response_model=PaymentMethodListResponse, 
    summary="Listar, filtrar y paginar métodos de pago"
) 
def list_payment_methods(
    session: SessionDep,
    
    # Paginación
    page: int = Query(default=1, ge=1, description="Número de página."),
    page_size: int = Query(default=10, le=100, description="Tamaño de la página."),
    
    # Filtro de eliminación (Soft Delete) - Reemplaza el endpoint /deleted
    deleted: Optional[bool] = Query(default=False, description="Filtrar por estado de eliminación (True: Eliminados, False: Activos). Por defecto, solo muestra ACTIVOS."),
    
    # Búsqueda por nombre
    search_term: Optional[str] = Query(default=None, description="Buscar por nombre del método de pago (parcial).")
    
) -> PaymentMethodListResponse:

    offset = (page - 1) * page_size
    base_query = select(PaymentMethod)
    
    # 1. Aplicar Filtro de Eliminación (deleted)
    if deleted is not None:
        base_query = base_query.where(PaymentMethod.deleted == deleted)
    
    # 2. Aplicar Filtro de Búsqueda
    if search_term:
        search_filter = PaymentMethod.name.ilike(f"%{search_term}%")
        base_query = base_query.where(search_filter)

    # 3. Obtener conteo total (necesario para la paginación)
    # Ejecutamos la consulta base sin paginación para obtener el total de ítems filtrados
    total_items = len(session.exec(base_query).all()) 
    
    # 4. Aplicar Paginación
    final_query = base_query.offset(offset).limit(page_size)

    payment_methods_db = session.exec(final_query).all()

    # Manejo de páginas vacías
    if not payment_methods_db and page > 1 and total_items > 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontraron métodos de pago en esta página.",
        )

    # Convertir a esquema de lectura
    items_read = [PaymentMethodRead.model_validate(item) for item in payment_methods_db]

    total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 0

    return PaymentMethodListResponse(
        items=items_read,
        total_items=total_items,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

# ----------------------------------------------------------------------
# --- RUTA DE LECTURA POR ID (GET /{id}) ---
# ----------------------------------------------------------------------

@router.get("/{method_id}", response_model=PaymentMethodRead, summary="Obtener método de pago activo por ID")
def read_payment_method(method_id: int, session: SessionDep):
    """Obtiene un método de pago específico por su ID. Solo devuelve métodos activos."""
    try:
        method_db = session.get(PaymentMethod, method_id)
        
        # Política de filtrado: El método no debe existir o estar eliminado
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

@router.post("", response_model=PaymentMethodRead, status_code=status.HTTP_201_CREATED, summary="Crear nuevo método de pago")
def create_payment_method(method_data: PaymentMethodCreate, session: SessionDep):
    """Crea un nuevo método de pago, validando que el nombre sea único entre los activos."""
    try:
        # Política de unicidad: Validación de Unicidad por nombre (solo para registros activos)
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
        current_time = datetime.now(timezone.utc)
        method_db.created_at = current_time
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
            detail=f"Error al crear el método de pago: {str(e)}",
        )

# --- RUTA PARA ACTUALIZACIÓN (PATCH) ---

@router.patch("/{method_id}", response_model=PaymentMethodRead, summary="Actualizar método de pago activo")
def update_payment_method(method_id: int, method_data: PaymentMethodUpdate, session: SessionDep):
    """Actualiza el nombre del método de pago, manteniendo la unicidad."""
    try:
        method_db = session.get(PaymentMethod, method_id)
        current_time = datetime.now(timezone.utc)

        # Política de filtrado: El método a actualizar no debe existir o estar eliminado
        if not method_db or method_db.deleted is True:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Método de pago no encontrado o eliminado."
            )
        
        data_to_update = method_data.model_dump(exclude_unset=True)
        
        # Validación de unicidad si se intenta cambiar el nombre
        if "name" in data_to_update and data_to_update["name"] != method_db.name:
            # Política de unicidad: Busca conflictos solo entre registros activos
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
            detail=f"Error al actualizar el método de pago: {str(e)}",
        )

# --- RUTA PARA ELIMINACIÓN SUAVE (DELETE) ---

@router.delete("/{method_id}", status_code=status.HTTP_200_OK, response_model=dict, summary="Eliminación suave de un método de pago")
def soft_delete_payment_method(method_id: int, session: SessionDep):
    """Realiza la 'Eliminación Suave' de un método de pago, marcando 'deleted=True'."""
    try:
        method_db = session.get(PaymentMethod, method_id)
        current_time = datetime.now(timezone.utc)

        if not method_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Método de pago no encontrado."
            )
        
        # Política de estado: Si ya está eliminado, informa
        if method_db.deleted is True:
            return {"message": f"El Método de Pago (ID: {method_id}) ya estaba marcado como eliminado."}

        # Aplicar Soft Delete
        method_db.deleted = True
        method_db.deleted_on = current_time
        method_db.updated_at = current_time
        session.add(method_db)
        session.commit()
        
        return {"message": f"Método de Pago: {method_db.name} (ID: {method_id}) eliminado (Soft Delete) exitosamente el {current_time.isoformat()}."}
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar el método de pago: {str(e)}",
        )

# --- RUTA PARA RESTAURACIÓN (PATCH /restore) ---

@router.patch("/{method_id}/restore", response_model=PaymentMethodRead, summary="Restaurar método de pago eliminado")
def restore_deleted_payment_method(method_id: int, session: SessionDep):
    """
    Restaurar un método de pago previamente eliminado (Soft Delete).
    """
    try:
        method_db = session.get(PaymentMethod, method_id)
        current_time = datetime.now(timezone.utc)

        if not method_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Método de pago no encontrado."
            )
        
        # Política de estado: Solo permite la restauración si está actualmente eliminado
        if method_db.deleted is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="El método de pago no está eliminado y no puede ser restaurado."
            )

        # Política de unicidad: Verificar si el nombre está ocupado por otro método activo antes de restaurar
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

        # Restaurar el método
        method_db.deleted = False
        method_db.deleted_on = None 
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
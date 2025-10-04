from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlmodel import select
from datetime import datetime
from typing import List, Optional, Dict, Any 

# Importa las dependencias del Core
from core.database import SessionDep
from core.security import decode_token 

from models.clients import Client 
from schemas.clients_schema import ClientCreate, ClientRead, ClientUpdate 

# Configuración del Router con prefijo y dependencia de autenticación
router = APIRouter(
    prefix="/api/clients", 
    tags=["CLIENTS"], 
    dependencies=[Depends(decode_token)] 
) 


# 1. Obtener lista de clientes (GET) - CORREGIDO Y OPTIMIZADO
@router.get("",
            response_model=Dict[str, Any], # CORREGIDO: Retorna diccionario con data y metadata
            summary="Listar y filtrar clientes con paginación"
            )
def list_clients(
    session: SessionDep,
    
    # Paginación
    offset: int = Query(default=0, ge=0, description="Número de registros a omitir (offset)."),
    limit: int = Query(default=10, le=100, description="Máxima cantidad de clientes a retornar (limit)."),
    
    # Filtro de Estado
    deleted_filter: Optional[bool] = Query(default=False, alias="deleted", description="Filtra por clientes eliminados (True). Por defecto, solo activos (False)."),
    
    # Búsqueda/Filtro
    name_search: Optional[str] = Query(default=None, description="Buscar por nombre de cliente (parcialmente)."),

    # Busqueda por numero de identificación
    identification_search: Optional[str] = Query(default=None, description="Buscar por número de identificación (parcialmente)."),

    #Busqueda por correo electrónico
    email_search: Optional[str] = Query(default=None, description="Buscar por correo electrónico (parcialmente)."),
    
    #Busqueda por número telefónico
    phone_search: Optional[str] = Query(default=None, description="Buscar por número telefónico (parcialmente)."),
    
):
    """
    Obtiene una lista paginada y filtrada de clientes, incluyendo el conteo total de registros.
    """
    try:
        # 1. INICIALIZAR LA CONSULTA BASE
        query = select(Client) 
        
        # 2. APLICAR FILTRO DE ESTADO
        if deleted_filter is not None:
            query = query.where(Client.deleted == deleted_filter)
        
        # 3. APLICAR FILTROS DE BÚSQUEDA
        if name_search:
            # NOTA: Se corrige a 'Client.name' asumiendo que es el campo correcto.
            query = query.where(Client.fullname.ilike(f"%{name_search}%")) 
        
        if identification_search:
            query = query.where(Client.identification_number.ilike(f"%{identification_search}%"))
        
        if email_search:
            query = query.where(Client.email.ilike(f"%{email_search}%"))
        
        if phone_search:
            query = query.where(Client.phone_number.ilike(f"%{phone_search}%"))
        
        # 4. OBTENER CONTEO TOTAL (antes de la paginación)
        # Se obtiene todos los IDs/Objetos para el conteo después de filtrar.
        total_count = len(session.exec(query).all())
        
        # 5. APLICAR PAGINACIÓN
        final_statement = query.limit(limit).offset(offset)
        clients = session.exec(final_statement).all()
        
        # 6. RETORNAR RESULTADO CON METADATA
        return {
            "data": clients,
            "metadata": {
                "total_count": total_count,
                "limit": limit,
                "offset": offset
            }
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar los clientes: {str(e)}",
        )


# 2. Obtener un cliente en particular (GET)
@router.get("/{client_id}", response_model=ClientRead)
def read_client(client_id: int, session: SessionDep):
    """Obtiene un cliente específico por su ID. Solo devuelve clientes activos."""
    try:
        client_db = session.get(Client, client_id)
        
        # Validación de existencia y de eliminación suave (debe existir y no estar eliminada)
        if not client_db or client_db.deleted is True:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Cliente no encontrado o eliminado."
            )
        return client_db
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al leer el cliente: {str(e)}",
        )

# 3. Crear un nuevo cliente (POST)
@router.post("", response_model=ClientRead, status_code=status.HTTP_201_CREATED)
def create_client(client_data: ClientCreate, session: SessionDep):
    """Crea un nuevo cliente, verificando unicidad de campos sensibles (activos)."""
    try:
        # Validación de unicidad para campos clave (phone, identification, email) entre clientes activos
        def check_uniqueness(field, value):
            existing = session.exec(
                select(Client).where(field == value).where(Client.deleted == False)
            ).first()
            if existing:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"El {client_data.fullname} ya existe para un cliente activo.")

        # Verificar unicidad de campos
        if client_data.phone_number:
            check_uniqueness(Client.phone_number, client_data.phone_number)
        if client_data.identification_number:
            check_uniqueness(Client.identification_number, client_data.identification_number)
        if client_data.email:
            check_uniqueness(Client.email, client_data.email)
        
        # Crear el objeto (deleted=False y deleted_on=None por defecto en el modelo)
        client_db = Client.model_validate(client_data.model_dump())
        client_db.created_at = datetime.utcnow()
        client_db.updated_at = datetime.utcnow()

        session.add(client_db)
        session.commit()
        session.refresh(client_db)
        return client_db

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback() 
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear el cliente: {str(e)}",
        )


# 4. Actualizar parcialmente un cliente (PATCH)
@router.patch("/{client_id}", response_model=ClientRead)
def update_client(client_id: int, client_data: ClientUpdate, session: SessionDep):
    """Actualiza campos de un cliente activo, respetando la unicidad."""
    try:
        client_db = session.get(Client, client_id)

        # Validación: El cliente debe existir y no estar eliminado
        if not client_db or client_db.deleted is True:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Cliente no encontrado o eliminado."
            )
        
        data_to_update = client_data.model_dump(exclude_unset=True)

        # Validación de unicidad para campos clave si se están actualizando
        def check_update_uniqueness(field, value):
            existing = session.exec(
                select(Client).where(field == value).where(Client.deleted == False)
            ).first()
            # Si se encuentra un registro con el mismo valor Y no es el cliente actual
            if existing and existing.id != client_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"El {client_data.fullname} ya existe para otro cliente activo.")

        if "phone_number" in data_to_update and data_to_update["phone_number"] != client_db.phone_number:
            check_update_uniqueness(Client.phone_number, data_to_update["phone_number"])
            
        if "identification_number" in data_to_update and data_to_update["identification_number"] != client_db.identification_number:
            check_update_uniqueness(Client.identification_number, data_to_update["identification_number"])
            
        if "email" in data_to_update and data_to_update["email"] != client_db.email:
            check_update_uniqueness(Client.email, data_to_update["email"])

        # Aplicar la actualización y el timestamp
        client_db.sqlmodel_update(data_to_update)
        client_db.updated_at = datetime.utcnow()
        
        session.add(client_db)
        session.commit()
        session.refresh(client_db)
        return client_db
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar el cliente: {str(e)}",
        )

# 5. Eliminación Suave (DELETE)
@router.delete("/{client_id}", status_code=status.HTTP_200_OK, response_model=dict)
def soft_delete_client(client_id: int, session: SessionDep):
    """
    Realiza la 'Eliminación Suave' (Soft Delete) marcando 'deleted=True' y 'deleted_on'.
    """
    try:
        client_db = session.get(Client, client_id)

        if not client_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Cliente no encontrado."
            )
        
        if client_db.deleted is True:
            return {"message": f"El Cliente (ID: {client_id}) ya estaba marcado como eliminado."}

        current_time = datetime.utcnow()

        # Aplicar Soft Delete
        client_db.deleted = True
        client_db.deleted_on = current_time 
        client_db.updated_at = current_time 

        session.add(client_db)
        session.commit()

        return {"message": f"Cliente {client_db.fullname} (ID: {client_id}) eliminado (Soft Delete) exitosamente el {current_time.isoformat()}."}
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar el cliente: {str(e)}",
        )

# 6. Restaurar un cliente eliminado (PATCH)
# Ruta: /api/clients/{client_id}/restore
@router.patch("/{client_id}/restore", response_model=ClientRead)
def restore_deleted_client(client_id: int, session: SessionDep):
    """
    Restaura un cliente previamente eliminado (Soft Delete) 
    cambiando 'deleted' a False y limpiando 'deleted_on'.
    """
    try:
        client_db = session.get(Client, client_id)

        if not client_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Cliente no encontrado."
            )
        
        # Solo permite la restauración si está actualmente eliminado
        if client_db.deleted is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="El cliente no está eliminado y no puede ser restaurado."
            )

        # Antes de restaurar, verifica unicidad para evitar colisiones con clientes activos.
        
        def check_restore_uniqueness(field, value):
            existing = session.exec(
                select(Client).where(field == value).where(Client.deleted == False)
            ).first()
            if existing:
                # Si existe un cliente activo con el mismo valor, la restauración falla
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Conflicto: No se puede restaurar. El {client_db.fullname} '{value}' ya está en uso por otro cliente activo (ID: {existing.id}).")

        check_restore_uniqueness(Client.phone_number, client_db.phone_number)
        check_restore_uniqueness(Client.identification_number, client_db.identification_number)
        check_restore_uniqueness(Client.email, client_db.email)


        current_time = datetime.utcnow()

        # Restaurar el cliente
        client_db.deleted = False
        client_db.deleted_on = None  # Limpia la marca de tiempo de eliminación
        client_db.updated_at = current_time 

        session.add(client_db)
        session.commit()
        session.refresh(client_db)

        return client_db
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al restaurar el cliente: {str(e)}",
        )
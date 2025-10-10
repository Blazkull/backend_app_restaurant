from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlmodel import select, func # Importar func para conteo
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone # Usar timezone para consistencia
from typing import List, Optional
from starlette.responses import Response

# Importa las dependencias del Core
from core.database import SessionDep
from core.security import decode_token 

# Asume que estos modelos y schemas están definidos correctamente
from models.locations import Location
from models.status import Status
from models.tables import Table 
# Es necesario importar Status, Location, y User para las validaciones
# from models.status import Status 
# from models.locations import Location 
# from models.users import User 
from models.users import User
from schemas.tables_schema import TableCreate, TableListResponse, TableRead, TableUpdate, TableStatusUpdate # Asumiendo TableStatusUpdate existe

# Configuración del Router
router = APIRouter(prefix="/api/tables", tags=["TABLES"], dependencies=[Depends(decode_token)]) 

CAPACITY_MAX = 20

# ----------------------------------------------------------------------
# ENDPOINT 1: LISTAR Y FILTRAR MESAS ACTIVAS (GET /tables)
# ----------------------------------------------------------------------


@router.get("", response_model=TableListResponse, summary="Listar y filtrar mesas activas con paginación")
def list_tables(
    session: SessionDep,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=10, le=100),
    name_search: Optional[str] = Query(default=None, description="Buscar por nombre/número de mesa (parcialmente)."),
    status_id: Optional[int] = Query(default=None, description="Filtrar por ID de estado de la mesa."),
    status_name: Optional[str] = Query(default=None, description="Filtrar por nombre del estado de la mesa."),
    location_id: Optional[int] = Query(default=None, description="Filtrar por ID de ubicación de la mesa."),
    location_name: Optional[str] = Query(default=None, description="Filtrar por nombre de la ubicación de la mesa."),
    user_asigned_id: Optional[int] = Query(default=None, description="Filtrar por ID de usuario asignado a la mesa."),
    capacity_min: Optional[int] = Query(default=None, ge=1, description="Capacidad mínima de la mesa."),
    capacity_max: Optional[int] = Query(default=None, ge=1, description="Capacidad máxima de la mesa.")
) -> TableListResponse:
    """
    Obtiene una lista de todas las mesas **activas** (deleted=False) aplicando filtros y paginación.
    """
    try:
        # Base Query
        base_query = select(Table).where(Table.deleted == False)
        count_query = select(func.count()).select_from(Table).where(Table.deleted == False)
        
        # --------------------------
        # Aplicar filtros dinámicos
        # --------------------------
        if name_search:
            filter_expr = Table.name.ilike(f"%{name_search}%")
            base_query = base_query.where(filter_expr)
            count_query = count_query.where(filter_expr)

        if status_id is not None:
            filter_expr = Table.id_status == status_id
            base_query = base_query.where(filter_expr)
            count_query = count_query.where(filter_expr)
        elif status_name:
            filter_expr = Table.status.has(name=status_name)
            base_query = base_query.where(filter_expr)
            count_query = count_query.where(filter_expr)

        if location_id is not None:
            filter_expr = Table.id_location == location_id
            base_query = base_query.where(filter_expr)
            count_query = count_query.where(filter_expr)
        elif location_name:
            filter_expr = Table.location.has(name=location_name)
            base_query = base_query.where(filter_expr)
            count_query = count_query.where(filter_expr)

        if user_asigned_id is not None:
            filter_expr = Table.id_user_assigned == user_asigned_id
            base_query = base_query.where(filter_expr)
            count_query = count_query.where(filter_expr)

        if capacity_min is not None:
            filter_expr = Table.capacity >= capacity_min
            base_query = base_query.where(filter_expr)
            count_query = count_query.where(filter_expr)

        if capacity_max is not None:
            filter_expr = Table.capacity <= capacity_max
            base_query = base_query.where(filter_expr)
            count_query = count_query.where(filter_expr)

        # --------------------------
        # Conteo total seguro
        # --------------------------
        count_result = session.exec(count_query).first()
        total_count = count_result[0] if count_result else 0

        if total_count == 0:
            return Response(status_code=status.HTTP_204_NO_CONTENT)

        # --------------------------
        # Paginación
        # --------------------------
        total_pages = (total_count + limit - 1) // limit
        current_page = (offset // limit) + 1

        if offset >= total_count:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El valor de 'offset' excede el número total de mesas activas disponibles que coinciden con el filtro."
            )

        # --------------------------
        # Consultar datos finales
        # --------------------------
        final_query = (
            base_query
            .order_by(Table.id.asc())
            .offset(offset)
            .limit(limit)
            .options(
                selectinload(Table.status),
                selectinload(Table.location),
                selectinload(Table.user_assigned)
            )
        )

        tables = session.exec(final_query).all()

        if not tables and offset > 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No se encontraron más mesas activas en el rango de paginación."
            )

        # --------------------------
        # Respuesta formateada
        # --------------------------
        return TableListResponse(
            items=tables,
            total_count=total_count,
            offset=offset,
            limit=limit,
            total_pages=total_pages,
            current_page=current_page
        )

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Error al listar las mesas: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al listar las mesas."
        )

# ----------------------------------------------------------------------
# ENDPOINT 2: LISTAR MESAS ELIMINADAS (GET /tables/deleted)
# ----------------------------------------------------------------------
@router.get("/deleted", response_model=List[TableRead], summary="Listar mesas marcadas como eliminadas")
def read_deleted_tables(
    session: SessionDep,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=10, le=100)
) -> List[TableRead]:
    """
    Lista solo las mesas cuyo campo 'deleted' es True, con paginación.
    """
    query = select(Table).where(Table.deleted == True).offset(offset).limit(limit).options(
        selectinload(Table.status), 
        selectinload(Table.location),
        selectinload(Table.user_assigned)
    )
    tables = session.exec(query).all()
    
    if not tables and offset > 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontraron mesas eliminadas en el rango de paginación."
        )
    
    return tables


# ----------------------------------------------------------------------
# ENDPOINT 3: OBTENER MESA POR ID (GET /tables/{table_id})
# ----------------------------------------------------------------------
@router.get("/{table_id}", response_model=TableRead, summary="Obtener una mesa por ID (excluye eliminadas)")
def read_table(table_id: int, session: SessionDep):
    """Obtiene una mesa específica por su ID, excluyendo las eliminadas."""
    try:
        statement = select(Table).where(
            Table.id == table_id, 
            Table.deleted == False
        ).options(
            selectinload(Table.status), 
            selectinload(Table.location),
            selectinload(Table.user_assigned)
        )
        table_db = session.exec(statement).first()
        
        if not table_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Mesa no encontrada o eliminada."
            )
        return table_db
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Error al leer la mesa: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al leer la mesa."
        )

# ----------------------------------------------------------------------
# ENDPOINT 4: CREAR MESA (POST /tables)
# ----------------------------------------------------------------------
@router.post("", response_model=TableRead, status_code=status.HTTP_201_CREATED, summary="Crea una nueva mesa")
def create_table(table_data: TableCreate, session: SessionDep):
    """Crea una nueva mesa, validando que el nombre sea único entre las activas."""
    try:
        # Validación de capacidad 
        # (Se corrigió la sintaxis de asignación condicional en Python 3.8+)
        if table_data.capacity is not None and (table_data.capacity > CAPACITY_MAX or table_data.capacity <= 0):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"La capacidad de la mesa debe ser un número positivo y no mayor a {CAPACITY_MAX}."
            )
            
        # Validación de Unicidad por nombre (solo para registros activos)
        existing_table = session.exec(
            select(Table)
            .where(Table.name == table_data.name)
            .where(Table.deleted == False)
        ).first()
            
        if existing_table:
            raise HTTPException(
               status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ya existe una mesa activa con el nombre/número: '{table_data.name}'." 
            )

        # Creación de la Mesa
        table_db = Table.model_validate(table_data.model_dump())
        table_db.created_at = datetime.now(timezone.utc) # Usar timezone.utc para consistencia
        table_db.updated_at = datetime.now(timezone.utc)
        # Se omiten las validaciones de FKs para no asumir los modelos, pero se recomienda incluirlas.

        session.add(table_db)
        session.commit()
        session.refresh(table_db)
        
        # Cargar relaciones para el response_model
        session.refresh(table_db, attribute_names=["status", "location", "user_assigned"])
        
        return table_db

    except HTTPException as http_exc:
        session.rollback() # Asegura el rollback si el error HTTP viene de una validación de base de datos
        raise http_exc
    except Exception as e:
        session.rollback() 
        print(f"Error al crear la mesa: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al crear la mesa."
        )

# ----------------------------------------------------------------------
# ENDPOINT 5: ACTUALIZAR MESA (PATCH /tables/{table_id})
# ----------------------------------------------------------------------
@router.patch("/{table_id}", response_model=TableRead, summary="Actualiza campos de la mesa")
def update_table(table_id: int, table_data: TableUpdate, session: SessionDep):
    """Actualiza campos de la mesa, manteniendo la unicidad del nombre."""
    try:
        table_db = session.get(Table, table_id)
        CAPACITY_MAX = 20
        
        # Validación: La mesa debe existir y no estar eliminada
        if not table_db or table_db.deleted is True:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Mesa no encontrada o eliminada."
            )
        
        # 1. Validación de capacidad (se corrigió la sintaxis)
        if table_data.capacity is not None:
            if table_data.capacity > CAPACITY_MAX or table_data.capacity <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail=f"La capacidad de la mesa debe ser un número positivo y no mayor a {CAPACITY_MAX}."
                )
        
        if not table_data.model_dump(exclude_unset=True):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="No se proporcionaron datos para actualizar."
            )
        if not session.get(Status , table_data.id_status) and table_data.id_status is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"El ID de estado '{table_data.id_status}' no existe."
            )
        if not session.get(Location , table_data.id_location) and table_data.id_location is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"El ID de ubicación '{table_data.id_location}' no existe."
            )
        if not session.get(User , table_data.id_user_assigned) and table_data.id_user_assigned is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"El ID de usuario asignado '{table_data.id_user_assigned}' no existe."
            )
        
        if table_data.name is not None and table_data.name.strip() == "":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="El nombre/número de la mesa no puede estar vacío."
            )
        
        data_to_update = table_data.model_dump(exclude_unset=True)
        
        # 2. Validación de unicidad si se intenta cambiar el nombre
        if "name" in data_to_update and data_to_update["name"] != table_db.name:
            existing_table = session.exec(
                select(Table)
                .where(Table.name == data_to_update["name"])
                .where(Table.deleted == False)
            ).first()
            
            # Si el nombre existe Y no pertenece a la mesa que estamos actualizando
            if existing_table:
                # No es necesario el check de ID, ya que la mesa actual NO está eliminada
                # y estamos buscando sólo mesas activas. El error es inmediato.
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ya existe otra mesa activa con el nombre/número: '{data_to_update['name']}'."
                )
        
        # 3. Aplicar actualización y actualizar timestamp
        table_db.sqlmodel_update(data_to_update)
        table_db.updated_at = datetime.now(timezone.utc)
        
        session.add(table_db)
        session.commit()
        session.refresh(table_db)
        
        # Cargar relaciones para el response_model
        session.refresh(table_db, attribute_names=["status", "location", "user_assigned"])

        return table_db
    
    except HTTPException as http_exc:
        session.rollback()
        raise http_exc
    except Exception as e:
        session.rollback()
        print(f"Error al actualizar la mesa: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al actualizar la mesa."
        )

# ----------------------------------------------------------------------
# ENDPOINT 6: ELIMINAR MESA (DELETE /tables/{table_id}) - SOFT DELETE
# ----------------------------------------------------------------------
@router.delete("/{table_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Realiza la eliminación suave de una mesa")
def soft_delete_table(table_id: int, session: SessionDep):
    """Realiza la 'Eliminación Suave' de una mesa, marcando 'deleted=True'."""
    try:
        table_db = session.get(Table, table_id)

        if not table_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Mesa no encontrada."
            )
        
        # Si ya está eliminada, retorna 204 (idempotente)
        if table_db.deleted is True:
            return Response(status_code=status.HTTP_204_NO_CONTENT)

        current_time = datetime.now(timezone.utc)

        # Aplicar Soft Delete
        table_db.deleted = True
        table_db.deleted_on = current_time
        table_db.updated_at = current_time
        session.add(table_db)
        session.commit()
        
        return {"message": f"Mesa con ID {table_id} eliminada correctamente"}
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        print(f"Error al eliminar la mesa: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al eliminar la mesa."
        )

# ----------------------------------------------------------------------
# ENDPOINT 7: RESTAURAR MESA (PATCH /tables/{table_id}/restore)
# ----------------------------------------------------------------------
@router.patch("/{table_id}/restore", response_model=TableRead, summary="Restaura una mesa previamente eliminada")
def restore_deleted_table(table_id: int, session: SessionDep):
    """
    Restaura una mesa eliminada, cambiando 'deleted' a False y limpiando 'deleted_on', y valida unicidad del nombre.
    """
    try:
        table_db = session.get(Table, table_id)

        if not table_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Mesa no encontrada."
            )
        
        # Si no está eliminada, devolvemos el objeto (idempotente)
        if table_db.deleted is False:
             # Cargar relaciones antes de devolver
            session.refresh(table_db, attribute_names=["status", "location", "user_assigned"])
            return table_db

        # 1. Validación de unicidad: Verificar si el nombre está ocupado por otra mesa activa
        existing_table = session.exec(
            select(Table)
            .where(Table.name == table_db.name)
            .where(Table.deleted == False)
        ).first()

        if existing_table:
            # CORRECCIÓN: Usar 409 CONFLICT que es más apropiado que 400 BAD REQUEST para unicidad
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail=f"Conflicto: No se puede restaurar. El nombre '{table_db.name}' ya está en uso por otra mesa activa (ID: {existing_table.id}). Por favor, actualice el nombre de la mesa antes de restaurarla."
            )

        current_time = datetime.now(timezone.utc)

        # 2. Restaurar la mesa
        table_db.deleted = False
        table_db.deleted_on = None 
        table_db.updated_at = current_time 

        session.add(table_db)
        session.commit()
        session.refresh(table_db)
        
        # Cargar relaciones para el response_model
        session.refresh(table_db, attribute_names=["status", "location", "user_assigned"])

        return table_db
    
    except HTTPException as http_exc:
        session.rollback()
        raise http_exc
    except Exception as e:
        session.rollback()
        print(f"Error al restaurar la mesa: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al restaurar la mesa."
        )

# ----------------------------------------------------------------------
# ENDPOINT 8: CAMBIAR SOLO EL ESTADO DE LA MESA (PATCH /tables/{table_id}/status)
# ----------------------------------------------------------------------
@router.patch(
    "/{table_id}/status", 
    response_model=TableRead, 
    summary="Actualiza únicamente el ID del estado de la mesa"
)
def update_table_status(
    table_id: int, 
    table_status: TableStatusUpdate, 
    session: SessionDep
):
    """
    Cambia el estado (id_status) de una mesa activa por su ID.
    """
    try:
        table_db = session.get(Table, table_id)

        # Validación: La mesa debe existir y no estar eliminada
        if not table_db or table_db.deleted is True:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Mesa no encontrada o eliminada."
            )
        
        # Si el nuevo ID es el mismo que el actual, cargamos relaciones y devolvemos la mesa
        if table_db.id_status == table_status.id_status:
            session.refresh(table_db, attribute_names=["status", "location", "user_assigned"])
            return table_db
        

        # Aplicar actualización y actualizar timestamp
        table_db.id_status = table_status.id_status
        table_db.updated_at = datetime.now(timezone.utc)
        
        session.add(table_db)
        session.commit()
        session.refresh(table_db)
        
        # Cargar relaciones para el response_model
        session.refresh(table_db, attribute_names=["status", "location", "user_assigned"])
        
        return table_db
    
    except HTTPException as http_exc:
        session.rollback()
        raise http_exc
    except Exception as e:
        session.rollback()
        print(f"Error al actualizar el estado de la mesa: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al actualizar el estado de la mesa."
        )
    
# ----------------------------------------------------------------------
# ENDPOINT 9: REASIGNAR USUARIO A UNA MESA (PATCH /tables/{table_id}/assign)
# ----------------------------------------------------------------------
@router.patch(
    "/{table_id}/assign",
    response_model=TableRead,
    summary="Reasigna un usuario (mesero o encargado) a una mesa activa"
)
def assign_user_to_table(
    table_id: int,
    user_data: dict,  # Espera { "id_user_assigned": int }
    session: SessionDep
):
    """
    Reasigna la mesa a un nuevo usuario (por ejemplo, mesero).
    Valida que la mesa exista, no esté eliminada y que el usuario exista.
    """
    try:
        # Extraer id_user_assigned del cuerpo
        new_user_id = user_data.get("id_user_assigned")
        if not new_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debe proporcionar el campo 'id_user_assigned' con un valor válido."
            )

        # Validar mesa
        table_db = session.get(Table, table_id)
        if not table_db or table_db.deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mesa no encontrada o eliminada."
            )

        # Validar usuario
        user_db = session.get(User, new_user_id)
        if not user_db:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El usuario con ID {new_user_id} no existe."
            )

        # Validar que no sea el mismo usuario
        if table_db.id_user_assigned == new_user_id:
            session.refresh(table_db, attribute_names=["status", "location", "user_assigned"])
            return table_db

        # Actualizar asignación
        table_db.id_user_assigned = new_user_id
        table_db.updated_at = datetime.now(timezone.utc)

        session.add(table_db)
        session.commit()
        session.refresh(table_db)

        # Cargar relaciones
        session.refresh(table_db, attribute_names=["status", "location", "user_assigned"])

        return table_db

    except HTTPException as http_exc:
        session.rollback()
        raise http_exc
    except Exception as e:
        session.rollback()
        print(f"Error al reasignar usuario a la mesa: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al reasignar el usuario a la mesa."
        )

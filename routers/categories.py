from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlmodel import select
from datetime import datetime
from typing import List, Optional, Dict, Any 

# Importa las dependencias del Core
from core.database import SessionDep
from core.security import decode_token 

# Importa el modelo y los schemas actualizados
from models.categories import Category 
from schemas.categories_schema import CategoryCreate, CategoryRead, CategoryUpdate 

# Configuración del Router con prefijo y dependencia de autenticación
router = APIRouter(
    prefix="/api/categories", 
    tags=["CATEGORIES"], 
    dependencies=[Depends(decode_token)] # Autenticación global para todos los endpoints
) 

# --- ENDPOINTS ---

# 1. Obtener lista de categorías (GET) - CON PAGINACIÓN Y FILTROS
# Ruta: /api/categories
@router.get("", 
            response_model=Dict[str, Any], 
            summary="Listar, filtrar y paginar categorías"
           )
def list_categories(
    session: SessionDep,
    
    # Paginación
    offset: int = Query(default=0, ge=0, description="Número de registros a omitir (offset)."),
    limit: int = Query(default=10, le=100, description="Máxima cantidad de categorías a retornar (limit)."),
    
    # Filtro de Estado por nombre (string)
    status_filter: Optional[str] = Query(default="Activo", description="Filtra por el estado de la categoría: 'Activo' o 'Inactivo'. (Valor por defecto: 'Activo')"),
    
    # Búsqueda/Filtro por nombre
    name_search: Optional[str] = Query(default=None, description="Buscar por nombre de categoría (parcialmente)."),
):
    """
    Obtiene una lista paginada y filtrada de categorías, incluyendo el conteo total de registros.
    """
    try:
        # 1. INICIALIZAR LA CONSULTA BASE
        query = select(Category) 
        
        # 2. APLICAR FILTRO DE ESTADO POR NOMBRE
        if status_filter:
            status_filter_lower = status_filter.lower()
            
            # **NOTA: Se corrigió la comparación a minúsculas ("inactivo" y "activo")**
            if status_filter_lower == "inactivo":
                # Si el filtro es 'Inactivo' (eliminada), buscamos Category.deleted == True
                query = query.where(Category.deleted == True)
            elif status_filter_lower == "activo":
                # Si el filtro es 'Activo' (no eliminada), buscamos Category.deleted == False
                query = query.where(Category.deleted == False)
            else:
                # Error si se introduce un valor no reconocido
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El filtro de estado solo acepta 'Activo' o 'Inactivo'."
                )
        
        # 3. APLICAR FILTROS DE BÚSQUEDA POR NOMBRE
        if name_search:
            # Uso de ilike para búsqueda parcial e insensible a mayúsculas/minúsculas
            query = query.where(Category.name.ilike(f"%{name_search}%")) 
        
        # 4. OBTENER CONTEO TOTAL (antes de la paginación)
        total_count = len(session.exec(query).all())
        
        # 5. APLICAR PAGINACIÓN
        final_statement = query.limit(limit).offset(offset)
        categories = session.exec(final_statement).all()
        
        # 6. RETORNAR RESULTADO CON METADATA
        return {
            "data": categories,
            "metadata": {
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "status": status_filter,
                "name_search": name_search
            }
        }
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar las categorías: {str(e)}",
        )

# 2. Obtener una categoría en particular (GET)
# Ruta: /api/categories/{category_id}
@router.get("/{category_id}", response_model=CategoryRead)
def read_category(category_id: int, session: SessionDep):
    """Obtiene una categoría específica por su ID, con validación de existencia y estado."""
    try:
        category_db = session.get(Category, category_id)
        
        # Validación de existencia y de eliminación suave (debe existir y no estar eliminada)
        if not category_db or category_db.deleted is True:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Categoría no encontrada o eliminada."
            )
        return category_db
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al leer la categoría: {str(e)}",
        )

# 3. Crear una nueva categoría (POST)
# Ruta: /api/categories
@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(category_data: CategoryCreate, session: SessionDep):
    """Crea una nueva categoría, validando que el nombre sea único entre las activas."""
    try:
        # Validación de unicidad por nombre (solo para categorías activas)
        existing_category = session.exec(
            select(Category)
            .where(Category.name == category_data.name)
            .where(Category.deleted == False)
        ).first()
        if existing_category:
            raise HTTPException(
               status_code=status.HTTP_400_BAD_REQUEST, 
               detail="Ya existe una categoría activa con este nombre." 
            )

        # Crear el objeto y asignar timestamps (deleted=False por defecto)
        category_db = Category.model_validate(category_data.model_dump())
        category_db.created_at = datetime.utcnow()
        category_db.updated_at = datetime.utcnow()

        session.add(category_db)
        session.commit()
        session.refresh(category_db)
        return category_db

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback() 
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear la categoría: {str(e)}",
        )


# 4. Actualizar parcialmente una categoría (PATCH)
# Ruta: /api/categories/{category_id}
@router.patch("/{category_id}", response_model=CategoryRead)
def update_category(category_id: int, category_data: CategoryUpdate, session: SessionDep):
    """Actualiza campos de una categoría, manteniendo la unicidad del nombre si se cambia."""
    try:
        category_db = session.get(Category, category_id)

        # Validación: La categoría debe existir y no estar eliminada
        if not category_db or category_db.deleted is True:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Categoría no encontrada o eliminada."
            )
        
        data_to_update = category_data.model_dump(exclude_unset=True)

        # Validación de unicidad si se está actualizando el nombre
        if "name" in data_to_update and data_to_update["name"] != category_db.name:
            existing_category = session.exec(
                select(Category)
                .where(Category.name == data_to_update["name"])
                .where(Category.deleted == False) # Solo verifica duplicados activos
            ).first()
            if existing_category and existing_category.id != category_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="Ya existe otra categoría activa con este nombre."
                )

        # Aplicar la actualización y el timestamp
        category_db.sqlmodel_update(data_to_update)
        category_db.updated_at = datetime.utcnow()
        
        session.add(category_db)
        session.commit()
        session.refresh(category_db)
        return category_db
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar la categoría: {str(e)}",
        )

# 5. Eliminación Suave (DELETE)
# Ruta: /api/categories/{category_id}
@router.delete("/{category_id}", status_code=status.HTTP_200_OK, response_model=dict)
def delete_category(category_id: int, session: SessionDep):
    """
    Realiza la 'Eliminación Suave' (Soft Delete) de una categoría 
    marcando 'deleted=True' y estableciendo 'deleted_on'.
    """
    try:
        category_db = session.get(Category, category_id)

        # 1. Validación de existencia
        if not category_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Categoría no encontrada."
            )
        
        # 2. Validación de estado (si ya está eliminada)
        if category_db.deleted is True:
            return {"message": f"La Categoría (ID: {category_id}) ya estaba marcada como eliminada."}

        current_time = datetime.utcnow()

        # 3. Aplicar Soft Delete: Actualizar los campos
        category_db.deleted = True
        category_db.deleted_on = current_time # Captura la fecha de eliminación
        category_db.updated_at = current_time # Actualiza el timestamp de modificación

        session.add(category_db)
        session.commit()

        return {"message": f"Categoría: {category_db.name} (ID: {category_id}) eliminada (Soft Delete) exitosamente el {current_time.isoformat()}."}
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar la categoría: {str(e)}",
        )
    

# 6. Restauración de categoría (Restore)
# Ruta: /api/categories/{category_id}/restore
@router.patch("/{category_id}/restore", response_model=CategoryRead, summary="Restaura una categoría eliminada")
def restore_category(category_id: int, session: SessionDep):
    """
    Restaura una categoría que fue 'Eliminada Suavemente' (Soft Delete), 
    marcando 'deleted=False' y limpiando 'deleted_on'.
    """
    try:
        category_db = session.get(Category, category_id)

        # 1. Validación de existencia
        if not category_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Categoría no encontrada."
            )
        
        # 2. Validación de estado (si ya está activa)
        if category_db.deleted is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"La Categoría: {category_db.name} (ID: {category_id}) ya está activa y no necesita ser restaurada."
            )

        current_time = datetime.utcnow()

        # 3. Aplicar Restauración: Actualizar los campos
        category_db.deleted = False
        category_db.deleted_on = None # Limpia la fecha de eliminación
        category_db.updated_at = current_time # Actualiza el timestamp de modificación

        session.add(category_db)
        session.commit()
        session.refresh(category_db)

        return {
                "data": category_db,
                "response": {
                    "message": f"Categoría: {category_db.name} (ID: {category_id}) restaurada exitosamente el {current_time.isoformat()}."
                }
            }
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al restaurar la categoría: {str(e)}",
        )
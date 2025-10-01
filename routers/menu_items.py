from fastapi import APIRouter, Depends, status, HTTPException
from sqlmodel import select
from datetime import datetime
from typing import List, Optional

# Importa las dependencias del Core
from core.database import SessionDep
from core.security import decode_token 

from models.menu_items import MenuItem
from schemas.menu_items_schema import MenuItemCreate, MenuItemUpdate, MenuItemRead

# Configuración del Router
# Uso 'MENU' como tag para agrupar en la documentación de la API (Swagger/Redoc)
router = APIRouter(tags=["MENU"]) 


# Rutas para lectura (GET)
@router.get("/api/menu", response_model=List[MenuItemRead], dependencies=[Depends(decode_token)])
def list_menu_items(session: SessionDep):
    """
    Obtiene una lista de todos los elementos del menú que no han sido 
    eliminados (Soft Delete).
    """
    try:
        # Filtra por items donde deleted_at es NULL (no eliminados)
        statement = select(MenuItem).where(MenuItem.deleted_at == None)
        return session.exec(statement).all()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar los elementos del menú: {str(e)}",
        )

@router.get("/api/menu/{item_id}", response_model=MenuItemRead, dependencies=[Depends(decode_token)])
def read_menu_item(item_id: int, session: SessionDep):
    """Obtiene un elemento del menú por su ID."""
    try:
        menu_item_db = session.get(MenuItem, item_id)
        
        # Validación de existencia y de eliminación suave
        if not menu_item_db or menu_item_db.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Elemento del menú no encontrado."
            )
        return menu_item_db
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al leer el elemento del menú: {str(e)}",
        )

# Ruta para creacion (CREATE)
@router.post("/api/menu", response_model=MenuItemRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(decode_token)])
def create_menu_item(menu_item_data: MenuItemCreate, session: SessionDep):
    """Crea un nuevo elemento en el menú."""
    try:
        # Validación de unicidad por nombre (solo para ítems activos/no eliminados)
        existing_item = session.exec(
            select(MenuItem).where(MenuItem.name == menu_item_data.name).where(MenuItem.deleted_at == None)
        ).first()
        if existing_item:
            raise HTTPException(
               status_code=status.HTTP_400_BAD_REQUEST, detail="Ya existe un elemento del menú activo con este nombre." 
            )

        # Crear el objeto con timestamps iniciales
        menu_item_db = MenuItem.model_validate(menu_item_data.model_dump())
        menu_item_db.created_at = datetime.utcnow()
        menu_item_db.updated_at = datetime.utcnow()

        session.add(menu_item_db)
        session.commit()
        session.refresh(menu_item_db)
        return menu_item_db

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear el elemento del menú: {str(e)}",
        )

# Rutas para actualizar (PATCH)
@router.patch("/api/menu/{item_id}", response_model=MenuItemRead, dependencies=[Depends(decode_token)])
def update_menu_item(item_id: int, menu_item_data: MenuItemUpdate, session: SessionDep):
    """Actualiza campos de un elemento del menú."""
    try:
        menu_item_db = session.get(MenuItem, item_id)

        # Validación de existencia y de eliminación suave
        if not menu_item_db or menu_item_db.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Elemento del menú no encontrado."
            )
        
        # Obtener solo los campos que se van a actualizar
        item_data_dict = menu_item_data.model_dump(exclude_unset=True)

        # Validación de unicidad del nombre si se está actualizando
        if "name" in item_data_dict and item_data_dict["name"] != menu_item_db.name:
            existing_item = session.exec(
                select(MenuItem).where(MenuItem.name == item_data_dict["name"]).where(MenuItem.deleted_at == None)
            ).first()
            if existing_item and existing_item.id != item_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Ya existe un elemento del menú activo con ese nombre."
                )

        # Aplicar la actualización y el timestamp de actualización
        menu_item_db.sqlmodel_update(item_data_dict)
        menu_item_db.updated_at = datetime.utcnow()
        
        session.add(menu_item_db)
        session.commit()
        session.refresh(menu_item_db)
        return menu_item_db
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar el elemento del menú: {str(e)}",
        )

# Ruta para eliminacion (DELETE - Soft Delete)
@router.delete("/api/menu/{item_id}", status_code=status.HTTP_200_OK, response_model=dict, dependencies=[Depends(decode_token)])
def delete_menu_item(item_id: int, session: SessionDep):
    """Realiza la 'Eliminación Suave' (Soft Delete) marcando el campo deleted_at."""
    try:
        menu_item_db = session.get(MenuItem, item_id)

        # Validación de existencia
        if not menu_item_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Elemento del menú no encontrado."
            )
        
        # Evita la doble eliminación
        if menu_item_db.deleted_at is not None:
            return {"message": f"El elemento '{menu_item_db.name}' (ID: {item_id}) ya estaba marcado como eliminado."}

        # Aplicar Soft Delete (establecer la fecha de eliminación)
        menu_item_db.deleted_at = datetime.utcnow()
        menu_item_db.updated_at = datetime.utcnow() 

        session.add(menu_item_db)
        session.commit()

        return {"message": f"Elemento del menú '{menu_item_db.name}' eliminado (Soft Delete) exitosamente."}
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar el elemento del menú: {str(e)}",
        )
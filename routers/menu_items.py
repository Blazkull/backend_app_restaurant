from fastapi import APIRouter, Depends, Query, HTTPException, status, UploadFile, File, Form
from sqlmodel import select, func
from typing import List, Optional
from datetime import datetime, timezone 
from sqlalchemy.orm import selectinload
from starlette.responses import Response
import shutil
from pathlib import Path


# --- Importaciones de Core ---
# Esta importación ahora funciona porque security.py ya no depende de ella
from core.database import SessionDep 
from core.security import decode_token 

# --- Importaciones de Modelos y Schemas ---
from models.menu_items import MenuItem
from models.categories import Category 
from models.status import Status        
from schemas.menu_items_schema import MenuItemCreate, MenuItemRead, MenuItemUpdate, MenuItemListResponse

# --- Configuración del Router ---
# La dependencia de autenticación se aplica a TODOS los endpoints del router
router = APIRouter(
    prefix="/api/menu_items", 
    tags=["MENU ITEMS"], 
    dependencies=[Depends(decode_token)] # <--- ÚNICA DEPENDENCIA DE SEGURIDAD
)

# --- Configuración de directorio para imágenes ---
UPLOAD_BASE_DIR = Path("static")
MENU_ITEMS_IMG_DIR = UPLOAD_BASE_DIR / "menu_items" / "img"
MENU_ITEMS_IMG_DIR.mkdir(parents=True, exist_ok=True) 

# Función auxiliar para construir la URL de la imagen
def get_image_url(image_filename: Optional[str]) -> Optional[str]:
    """Construye la URL pública del archivo estático."""
    if image_filename:
        return f"/static/menu_items/img/{image_filename}"
    return None

# ======================================================================
# ENDPOINT 1: LISTAR Y FILTRAR ÍTEMS DE MENÚ (GET /menu_items) -> SOLO ACTIVOS
# ======================================================================

@router.get(
    "", 
    response_model=MenuItemListResponse, 
    summary="Listar y filtrar ítems de menú activos con paginación"
)
def read_menu_items(
    session: SessionDep,
    
    # Paginación
    page: int = Query(default=1, ge=1, description="Número de página."),
    page_size: int = Query(default=10, le=100, description="Tamaño de la página."),
    
    # Filtrado por IDs
    category_id: Optional[int] = Query(default=None, description="Filtrar por ID de categoría."),
    status_id: Optional[int] = Query(default=None, description="Filtrar por ID de estado."),
    
    # Búsqueda
    search_term: Optional[str] = Query(default=None, description="Buscar por nombre o ingredientes (parcial)."),
    
    # Ordenamiento
    sort_by: Optional[str] = Query("name", description="Campo para ordenar (name, price, estimated_time)"),
    sort_order: Optional[str] = Query("asc", description="Orden de clasificación (asc, desc)")
    
) -> MenuItemListResponse:
    
    offset = (page - 1) * page_size
    base_query = select(MenuItem).where(MenuItem.deleted == False)
    count_query = select(func.count(MenuItem.id)).where(MenuItem.deleted == False)
    
    # Aplicar Filtros
    if category_id is not None:
        category_filter = MenuItem.id_category == category_id
        base_query = base_query.where(category_filter)
        count_query = count_query.where(category_filter)
        
    if status_id is not None:
        status_filter = MenuItem.id_status == status_id
        base_query = base_query.where(status_filter)
        count_query = count_query.where(status_filter)

    if search_term:
        search_filter = (MenuItem.name.ilike(f"%{search_term}%")) | (MenuItem.ingredients.ilike(f"%{search_term}%"))
        base_query = base_query.where(search_filter)
        count_query = count_query.where(search_filter)
        
    # Obtener conteo total
    total_items = session.exec(count_query).scalar_one_or_none() or 0

    # Aplicar Ordenación
    sort_column = getattr(MenuItem, sort_by, MenuItem.name)
    if sort_order.lower() == "desc":
        base_query = base_query.order_by(sort_column.desc())
    else:
        base_query = base_query.order_by(sort_column.asc())

    # Aplicar Paginación y Cargar Relaciones
    final_query = base_query.offset(offset).limit(page_size).options(
        selectinload(MenuItem.category),
        selectinload(MenuItem.status_rel)
    )
    
    menu_items_db = session.exec(final_query).all()
    
    if not menu_items_db and page > 1 and total_items > 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontraron ítems en esta página.",
        )
        
    # Post-procesar para añadir image_url
    for item in menu_items_db:
        item.image_url = get_image_url(item.image)
        
    total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 0

    return MenuItemListResponse(
        items=menu_items_db,
        total_items=total_items,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


# ----------------------------------------------------------------------
# ENDPOINT 2: LISTAR ÍTEMS ELIMINADOS (GET /menu_items/deleted)
# ----------------------------------------------------------------------

@router.get(
    "/deleted", 
    response_model=List[MenuItemRead], 
    summary="Listar ítems de menú eliminados"
)
def read_deleted_menu_items(
    session: SessionDep,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=10, le=100)
) -> List[MenuItemRead]:
    
    query = select(MenuItem).where(MenuItem.deleted == True).offset(offset).limit(limit).options(
        selectinload(MenuItem.category),
        selectinload(MenuItem.status_rel)
    )
    menu_items = session.exec(query).all()
    
    if not menu_items and offset > 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontraron ítems eliminados en el rango de paginación."
        )
    
    for item in menu_items:
        item.image_url = get_image_url(item.image)
    
    return menu_items


# ----------------------------------------------------------------------
# ENDPOINT 3: OBTENER ÍTEM POR ID (GET /menu_items/{item_id}) -> SOLO ACTIVOS
# ----------------------------------------------------------------------

@router.get("/{item_id}", response_model=MenuItemRead, summary="Obtener un ítem de menú por ID (excluye eliminados)")
def read_menu_item(item_id: int, session: SessionDep):
    
    query = select(MenuItem).where(
        MenuItem.id == item_id, 
        MenuItem.deleted == False 
    ).options(
        selectinload(MenuItem.category),
        selectinload(MenuItem.status_rel)
    )
    menu_item_db = session.exec(query).first()
    
    if not menu_item_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Menu item doesn't exist or is deleted."
        )
        
    menu_item_db.image_url = get_image_url(menu_item_db.image)
    return menu_item_db 

# ----------------------------------------------------------------------
# ENDPOINT 4: CREAR ÍTEM DE MENÚ (POST /menu_items)
# ----------------------------------------------------------------------

@router.post("", 
             response_model=MenuItemRead, 
             status_code=status.HTTP_201_CREATED, 
             summary="Crear nuevo ítem de menú con imagen"
)
async def create_menu_item_with_image(
    name: str = Form(..., max_length=100),
    id_category: int = Form(...),
    ingredients: str = Form(..., max_length=255),
    estimated_time: int = Form(...),
    price: float = Form(...),
    id_status: int = Form(...),
    image: Optional[UploadFile] = File(None, description="Archivo de imagen"),
    
    session: SessionDep
):
    try:
        # 1. Validaciones de FKs
        if not session.get(Category, id_category) or session.get(Category, id_category).deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoría no encontrada o eliminada.")
        if not session.get(Status, id_status) or session.get(Status, id_status).deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Estado no encontrado o eliminado.")

        # 2. Manejo y Guardado de la Imagen
        image_filename = None
        if image and image.filename:
            file_extension = Path(image.filename).suffix.lower()
            if file_extension not in [".jpg", ".jpeg", ".png", ".gif"]:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Formato de imagen no soportado.")
            
            safe_filename = f"menu_item_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{image.filename}"
            file_path = MENU_ITEMS_IMG_DIR / safe_filename
            
            with file_path.open("wb") as buffer:
                image.file.seek(0)
                shutil.copyfileobj(image.file, buffer)
            image_filename = safe_filename

        # 3. Creación del objeto MenuItem
        menu_item_data = MenuItemCreate(
            name=name, id_category=id_category, ingredients=ingredients, 
            estimated_time=estimated_time, price=price, id_status=id_status, image=image_filename
        )
        
        menu_db = MenuItem.model_validate(menu_item_data.model_dump())
        menu_db.created_at = datetime.now(timezone.utc)
        menu_db.updated_at = datetime.now(timezone.utc)
        
        # 4. Guardar
        session.add(menu_db)
        session.commit()
        session.refresh(menu_db)
        
        # Cargar relaciones para la respuesta
        session.refresh(menu_db, attribute_names=["category", "status_rel"]) 
        menu_db.image_url = get_image_url(menu_db.image)
        
        return menu_db
        
    except HTTPException as http_exc:
        session.rollback()
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear el ítem del menú: {str(e)}",
        )


# ----------------------------------------------------------------------
# ENDPOINT 5: ACTUALIZAR ÍTEM DE MENÚ (PATCH /menu_items/{item_id})
# ----------------------------------------------------------------------

@router.patch("/{item_id}", 
              response_model=MenuItemRead, 
              status_code=status.HTTP_200_OK, 
              summary="Actualizar ítem de menú (incluye cambio/eliminación de imagen)"
)
async def update_menu_item(
    item_id: int, 
    # Usamos Form/File para manejar el multipart/form-data
    name: Optional[str] = Form(None, max_length=100),
    id_category: Optional[int] = Form(None),
    ingredients: Optional[str] = Form(None, max_length=255),
    estimated_time: Optional[int] = Form(None),
    price: Optional[float] = Form(None),
    id_status: Optional[int] = Form(None),
    image: Optional[UploadFile] = File(None, description="Nueva imagen (Enviar campo vacío o 'null' para eliminar)"),
    
    session: SessionDep
):
    try:
        menu_db = session.get(MenuItem, item_id)
        if not menu_db:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item doesn't exist.")

        update_data = {}
        
        # 1. Validar y recolectar datos escalares
        if name is not None: update_data["name"] = name
        if ingredients is not None: update_data["ingredients"] = ingredients
        if estimated_time is not None: update_data["estimated_time"] = estimated_time
        if price is not None: update_data["price"] = price

        # 2. Validar FKs
        if id_category is not None:
            if not session.get(Category, id_category) or session.get(Category, id_category).deleted:
                 raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nueva categoría no encontrada o eliminada.")
            update_data["id_category"] = id_category
        
        if id_status is not None:
            if not session.get(Status, id_status) or session.get(Status, id_status).deleted:
                 raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nuevo estado no encontrado o eliminado.")
            update_data["id_status"] = id_status
            
        # 3. Manejo de la imagen
        new_image_filename = menu_db.image
        old_image_filename = menu_db.image
        
        if image is not None:
            if image.filename: 
                # Subir nueva imagen (y eliminar antigua)
                if old_image_filename:
                    old_path = MENU_ITEMS_IMG_DIR / old_image_filename
                    if old_path.exists(): old_path.unlink() 
                
                file_extension = Path(image.filename).suffix.lower()
                safe_filename = f"menu_item_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{image.filename}"
                file_path = MENU_ITEMS_IMG_DIR / safe_filename
                
                with file_path.open("wb") as buffer:
                    image.file.seek(0)
                    shutil.copyfileobj(image.file, buffer)
                new_image_filename = safe_filename
            else:
                # Eliminar imagen existente (el campo se envió vacío o nulo)
                if old_image_filename:
                    old_path = MENU_ITEMS_IMG_DIR / old_image_filename
                    if old_path.exists(): old_path.unlink()
                new_image_filename = None
        
        update_data["image"] = new_image_filename
        
        # 4. Aplicar actualización
        menu_db.sqlmodel_update(update_data)
        menu_db.updated_at = datetime.now(timezone.utc)
        
        session.add(menu_db)
        session.commit()
        session.refresh(menu_db)

        # Cargar relaciones y URL para la respuesta
        session.refresh(menu_db, attribute_names=["category", "status_rel"])
        menu_db.image_url = get_image_url(menu_db.image)
        
        return menu_db 
        
    except HTTPException as http_exc:
        session.rollback()
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar el ítem del menú: {str(e)}",
        )

# ----------------------------------------------------------------------
# ENDPOINT 6: ELIMINAR ÍTEM DE MENÚ (DELETE /menu_items/{item_id}) - SOFT DELETE
# ----------------------------------------------------------------------

@router.delete(
    "/{item_id}", 
    status_code=status.HTTP_204_NO_CONTENT, 
    summary="Eliminación suave de un ítem de menú (Soft Delete)"
)
def soft_delete_menu_item(item_id: int, session: SessionDep):
    
    try:
        menu_db = session.get(MenuItem, item_id)
        
        if not menu_db:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")
        
        if menu_db.deleted is True:
            return Response(status_code=status.HTTP_204_NO_CONTENT)

        current_time = datetime.now(timezone.utc)

        # Implementar Soft Delete
        menu_db.deleted = True
        menu_db.deleted_on = current_time 
        menu_db.updated_at = current_time 
        
        session.add(menu_db)
        session.commit()
        
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during soft delete: {str(e)}",
        )
        
# ----------------------------------------------------------------------
# ENDPOINT 7: RESTAURAR ÍTEM DE MENÚ (PATCH /menu_items/{item_id}/restore)
# ----------------------------------------------------------------------

@router.patch(
    "/{item_id}/restore", 
    response_model=MenuItemRead, 
    summary="Restaura un ítem de menú previamente eliminado"
)
def restore_deleted_menu_item(item_id: int, session: SessionDep):
    
    try:
        menu_db = session.get(MenuItem, item_id)

        if not menu_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Menu item not found."
            )
        
        if menu_db.deleted is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="The menu item is not deleted and cannot be restored."
            )

        current_time = datetime.now(timezone.utc)

        # Restaurar el ítem
        menu_db.deleted = False
        menu_db.deleted_on = None  # Limpia la marca de tiempo de eliminación
        menu_db.updated_at = current_time 

        session.add(menu_db)
        session.commit()
        session.refresh(menu_db)
        
        # Cargar relaciones y URL para la respuesta
        session.refresh(menu_db, attribute_names=["category", "status_rel"])
        menu_db.image_url = get_image_url(menu_db.image)

        return menu_db
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error restoring the menu item: {str(e)}",
        )
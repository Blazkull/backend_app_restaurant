from fastapi import APIRouter, Depends, Query, HTTPException, status, UploadFile, File, Form
from sqlmodel import select, func
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import selectinload
from starlette.responses import Response
import shutil
from pathlib import Path

# --- Importaciones de Core ---
from core.database import SessionDep
from core.security import decode_token

# --- Importaciones de Modelos y Schemas ---
from models.menu_items import MenuItem
from models.categories import Category
from models.status import Status
from schemas.menu_items_schema import MenuItemCreate, MenuItemRead, MenuItemUpdate, MenuItemListResponse

# --- Configuración del Router ---
router = APIRouter(
    prefix="/api/menu_items",
    tags=["MENU ITEMS"],
    dependencies=[Depends(decode_token)]
)

# --- Constantes de Validación ---
MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024 
ALLOWED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".webp"] # Añadido .webp

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

    # Filtrado por IDs/Nombres
    category_id: Optional[int] = Query(default=None, description="Filtrar por ID de categoría."),

    # Filtro de estado
    status_name: Optional[str] = Query(default='Activo', description="Filtrar por nombre de estado (e.g., 'Disponible', 'Agotado')."),

    # Búsqueda
    search_term: Optional[str] = Query(default=None, description="Buscar por nombre o ingredientes (parcial)."),

    # Ordenamiento
    sort_by: Optional[str] = Query("name", description="Campo para ordenar (name, price, estimated_time)"),
    sort_order: Optional[str] = Query("asc", description="Orden de clasificación (asc, desc)")

) -> MenuItemListResponse:

    offset = (page - 1) * page_size
    base_query = select(MenuItem).where(MenuItem.deleted == False)
    
    # 1. Aplicar Filtro por ID de Categoría
    if category_id is not None:
        category_filter = MenuItem.id_category == category_id
        base_query = base_query.where(category_filter)

    # 2. Aplicar Filtro por Nombre de Estado (Status Name)
    if status_name:
        status_name_lower = status_name.lower()

        # Buscar el ID del estado por nombre
        status_db = session.exec(
            select(Status.id)
            .where(func.lower(Status.name) == status_name_lower)
            .where(Status.deleted == False)
        ).first()

        if status_db is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"El estado con el nombre '{status_name}' no fue encontrado o está eliminado."
            )

        # Aplicar el filtro de estado usando el ID encontrado
        status_filter = MenuItem.id_status == status_db
        base_query = base_query.where(status_filter)

    # 3. Aplicar Filtro de Búsqueda
    if search_term:
        search_filter = (MenuItem.name.ilike(f"%{search_term}%")) | (MenuItem.ingredients.ilike(f"%{search_term}%"))
        base_query = base_query.where(search_filter)

    # Obtener conteo total (SOLICITADO)
    total_items = len(session.exec(base_query).all())

    # Aplicar Ordenación
    valid_sort_fields = ["name", "price", "estimated_time"]
    if sort_by not in valid_sort_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Campo de ordenamiento inválido: '{sort_by}'. Use uno de: {', '.join(valid_sort_fields)}."
        )

    sort_column = getattr(MenuItem, sort_by)

    if sort_order.lower() == "desc":
        base_query = base_query.order_by(sort_column.desc())
    else:
        base_query = base_query.order_by(sort_column.asc())

    # Aplicar Paginación y Cargar Relaciones
    final_query = base_query.offset(offset).limit(page_size).options(
        selectinload(MenuItem.category),
        selectinload(MenuItem.status)
    )

    menu_items_db = session.exec(final_query).all()

    if not menu_items_db and page > 1 and total_items > 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontraron ítems en esta página.",
        )

    # CORRECCIÓN DE ERROR: Convertir a MenuItemRead antes de añadir el campo calculado 'image_url'
    menu_items_read = []
    for item in menu_items_db:
        item_read = MenuItemRead.model_validate(item)
        item_read.image_url = get_image_url(item.image)
        menu_items_read.append(item_read)


    total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 0

    return MenuItemListResponse(
        items=menu_items_read,
        total_items=total_items,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

# ----------------------------------------------------------------------
# ENDPOINT 1.5: LISTAR TODOS LOS ÍTEMS DE MENÚ (GET /menu_items/all) -> INCLUYE ACTIVOS Y ELIMINADOS
# ----------------------------------------------------------------------

@router.get(
    "/all",
    response_model=MenuItemListResponse,
    summary="Listar *todos* los ítems de menú (incluye eliminados) con paginación simple"
)
def read_all_menu_items(
    session: SessionDep,
    page: int = Query(default=1, ge=1, description="Número de página."),
    page_size: int = Query(default=10, le=100, description="Tamaño de la página."),
    # El ordenamiento es opcional y se mantiene simple
    sort_by: Optional[str] = Query("name", description="Campo para ordenar (name, price, estimated_time, id)"),
    sort_order: Optional[str] = Query("asc", description="Orden de clasificación (asc, desc)")
) -> MenuItemListResponse:

    offset = (page - 1) * page_size
    # Consulta base: trae TODOS, sin filtro de deleted
    base_query = select(MenuItem)

    # Obtener conteo total (SOLICITADO)
    total_items = len(session.exec(base_query).all())

    # Aplicar Ordenación
    valid_sort_fields = ["name", "price", "estimated_time", "id"]
    if sort_by not in valid_sort_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Campo de ordenamiento inválido: '{sort_by}'. Use uno de: {', '.join(valid_sort_fields)}."
        )

    sort_column = getattr(MenuItem, sort_by)

    if sort_order.lower() == "desc":
        base_query = base_query.order_by(sort_column.desc())
    else:
        base_query = base_query.order_by(sort_column.asc())


    # Aplicar Paginación y Cargar Relaciones
    final_query = base_query.offset(offset).limit(page_size).options(
        selectinload(MenuItem.category),
        selectinload(MenuItem.status)
    )

    menu_items_db = session.exec(final_query).all()

    if not menu_items_db and page > 1 and total_items > 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontraron ítems en esta página.",
        )

    # CORRECCIÓN DE ERROR: Convertir a MenuItemRead antes de añadir el campo calculado 'image_url'
    menu_items_read = []
    for item in menu_items_db:
        item_read = MenuItemRead.model_validate(item)
        item_read.image_url = get_image_url(item.image)
        menu_items_read.append(item_read)

    total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 0

    return MenuItemListResponse(
        items=menu_items_read,
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
        selectinload(MenuItem.status)
    )
    menu_items_db = session.exec(query).all()
    
    if not menu_items_db and offset > 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontraron ítems eliminados en el rango de paginación."
        )

    # CORRECCIÓN DE ERROR
    menu_items_read = []
    for item in menu_items_db:
        item_read = MenuItemRead.model_validate(item)
        item_read.image_url = get_image_url(item.image)
        menu_items_read.append(item_read)


    return menu_items_read

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
        selectinload(MenuItem.status)
    )
    menu_item_db = session.exec(query).first()

    if not menu_item_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Menu item doesn't exist or is deleted."
        )

    # CORRECCIÓN DE ERROR
    item_read = MenuItemRead.model_validate(menu_item_db)
    item_read.image_url = get_image_url(menu_item_db.image)
    
    return item_read

# ----------------------------------------------------------------------
# ENDPOINT 4: CREAR ÍTEM DE MENÚ (POST /menu_items) - CON VALIDACIÓN DE 5MB Y FORMATO
# ----------------------------------------------------------------------

@router.post("",
    response_model=MenuItemRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo ítem de menú con imagen"
)
async def create_menu_item_with_image(
    session: SessionDep,
    name: str = Form(..., max_length=100),
    id_category: int = Form(...),
    ingredients: str = Form(..., max_length=255),
    estimated_time: int = Form(...),
    price: float = Form(...),
    id_status: int = Form(...),
    image: Optional[UploadFile] = File(None, description="Archivo de imagen"),

):
    try:
        # 1. Validaciones de FKs
        category_db = session.get(Category, id_category)
        if not category_db or category_db.deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoría no encontrada o eliminada.")
        
        status_obj = session.get(Status, id_status)
        if not status_obj or getattr(status_obj, 'deleted', False):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Estado no encontrado o eliminado.")

        # 2. Manejo y Guardado de la Imagen con VALIDACIÓN DE TAMAÑO y FORMATO
        image_filename = None
        if image and image.filename:
            
            # --- 2.1 VALIDACIÓN DE TAMAÑO (MAX 5MB) ---
            await image.seek(0)
            file_content = await image.read()
            file_size = len(file_content)

            if file_size > MAX_FILE_SIZE_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El tamaño del archivo ({file_size / (1024 * 1024):.2f} MB) excede el límite de {MAX_FILE_SIZE_MB} MB."
                )
            
            # --- 2.2. Validar Formato (AÑADIDO .webp) ---
            file_extension = Path(image.filename).suffix.lower()
            if file_extension not in ALLOWED_EXTENSIONS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail=f"Formato de imagen no soportado. Se permiten: {', '.join(ALLOWED_EXTENSIONS)}."
                )

            # --- 2.3. Guardar el archivo ---
            safe_filename = f"menu_item_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{image.filename}"
            file_path = MENU_ITEMS_IMG_DIR / safe_filename

            try:
                with file_path.open("wb") as buffer:
                    buffer.write(file_content)
            except Exception:
                 raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error interno al guardar la imagen en el servidor."
                 )
                 
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
        session.refresh(menu_db, attribute_names=["category", "status"])
        
        # Corrección de error: Convertir a MenuItemRead y añadir image_url
        item_read = MenuItemRead.model_validate(menu_db)
        item_read.image_url = get_image_url(menu_db.image)
        
        return item_read

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
# ENDPOINT 5: ACTUALIZAR ÍTEM DE MENÚ (PATCH /menu_items/{item_id}) - CON VALIDACIÓN DE 5MB Y FORMATO
# ----------------------------------------------------------------------

@router.patch("/{item_id}",
    response_model=MenuItemRead,
    status_code=status.HTTP_200_OK,
    summary="Actualizar ítem de menú (incluye cambio/eliminación de imagen)"
)
async def update_menu_item(
    session: SessionDep,
    item_id: int,
    # Usamos Form/File para manejar el multipart/form-data
    name: Optional[str] = Form(None, max_length=100),
    id_category: Optional[int] = Form(None),
    ingredients: Optional[str] = Form(None, max_length=255),
    estimated_time: Optional[int] = Form(None),
    price: Optional[float] = Form(None),
    id_status: Optional[int] = Form(None),
    image: Optional[UploadFile] = File(None, description="Nueva imagen (Enviar campo vacío o 'null' para eliminar)"),

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
            category_db = session.get(Category, id_category)
            if not category_db or category_db.deleted:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nueva categoría no encontrada o eliminada.")
            update_data["id_category"] = id_category

        if id_status is not None:
            status_obj = session.get(Status, id_status)
            if not status_obj or getattr(status_obj, 'deleted', False):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nuevo estado no encontrado o eliminado.")
            update_data["id_status"] = id_status

        # 3. Manejo de la imagen con VALIDACIÓN DE TAMAÑO y FORMATO
        new_image_filename = menu_db.image
        old_image_filename = menu_db.image

        if image is not None:
            if image.filename:
                
                # --- 3.1. VALIDACIÓN DE TAMAÑO (MAX 5MB) ---
                await image.seek(0)
                file_content = await image.read()
                file_size = len(file_content)

                if file_size > MAX_FILE_SIZE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"El tamaño del archivo ({file_size / (1024 * 1024):.2f} MB) excede el límite de {MAX_FILE_SIZE_MB} MB."
                    )
                
                # --- 3.2. Validar Formato (AÑADIDO .webp) ---
                file_extension = Path(image.filename).suffix.lower()
                if file_extension not in ALLOWED_EXTENSIONS:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST, 
                        detail=f"Formato de imagen no soportado. Se permiten: {', '.join(ALLOWED_EXTENSIONS)}."
                    )
                
                # Subir nueva imagen (y eliminar antigua)
                if old_image_filename:
                    old_path = MENU_ITEMS_IMG_DIR / old_image_filename
                    if old_path.exists(): old_path.unlink()

                safe_filename = f"menu_item_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{image.filename}"
                file_path = MENU_ITEMS_IMG_DIR / safe_filename
                
                # Guardar el contenido que ya leímos.
                try:
                    with file_path.open("wb") as buffer:
                        buffer.write(file_content)
                except Exception:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Error interno al guardar la nueva imagen en el servidor."
                    )
                    
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
        session.refresh(menu_db, attribute_names=["category", "status"])
        
        # Corrección de error: Convertir a MenuItemRead y añadir image_url
        item_read = MenuItemRead.model_validate(menu_db)
        item_read.image_url = get_image_url(menu_db.image)
        
        return item_read

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
# ENDPOINT 6: ELIMINAR ÍTEM DE MENÚ (DELETE /menu_items/{item_id}) - SOFT DELETE (ACTUALIZADO)
# ----------------------------------------------------------------------

@router.delete(
    "/{item_id}",
    status_code=status.HTTP_200_OK,
    response_model=dict,
    summary="Eliminación suave de un ítem de menú (Soft Delete) y confirmación"
)
def soft_delete_menu_item(item_id: int, session: SessionDep):
    """
    Realiza la 'Eliminación Suave' (Soft Delete) de un ítem de menú 
    marcando 'deleted=True' y estableciendo 'deleted_on'.
    """
    try:
        menu_db = session.get(MenuItem, item_id)

        # 1. Validación de existencia
        if not menu_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Ítem de menú no encontrado."
            )
        
        # 2. Validación de estado (si ya está eliminado)
        if menu_db.deleted is True:
            return {"message": f"El Ítem de Menú (ID: {item_id}) ya estaba marcado como eliminado."}

        current_time = datetime.now(timezone.utc)

        # 3. Aplicar Soft Delete: Actualizar los campos
        menu_db.deleted = True
        menu_db.deleted_on = current_time # Captura la fecha de eliminación
        menu_db.updated_at = current_time # Actualiza el timestamp de modificación

        session.add(menu_db)
        session.commit()

        return {
            "message": f"Ítem de Menú: {menu_db.name} (ID: {item_id}) eliminado (Soft Delete) exitosamente el {current_time.isoformat()}.",
            "item_id": item_id
        }
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar el ítem de menú: {str(e)}",
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
        menu_db.deleted_on = None
        menu_db.updated_at = current_time

        session.add(menu_db)
        session.commit()
        session.refresh(menu_db)

        # Cargar relaciones y URL para la respuesta
        session.refresh(menu_db, attribute_names=["category", "status"])
        
        # Corrección de error: Convertir a MenuItemRead y añadir image_url
        item_read = MenuItemRead.model_validate(menu_db)
        item_read.image_url = get_image_url(menu_db.image)
        
        return item_read

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error restoring the menu item: {str(e)}",
        )
from fastapi import APIRouter, Depends, status, HTTPException
from sqlmodel import select
from datetime import datetime
from typing import List, Optional, Dict, Any

# Importa dependencias del Core
from core.database import SessionDep
from core.security import decode_token 

# Asume que tienes un modelo InformationCompany
from models.information_company import InformationCompany 
from schemas.information_company_schema import InformationCompanyCreate, InformationCompanyRead, InformationCompanyUpdate 

# Configuración del Router
# Usaremos un único endpoint que opera sobre un recurso singular.
router = APIRouter(
    prefix="/api/company", 
    tags=["INFORMATION COMPANY"], 
    dependencies=[Depends(decode_token)]
) 

# --- FUNCIÓN AUXILIAR: Obtener el ÚNICO registro ---

def get_current_company_info(session: SessionDep) -> InformationCompany:
    """Busca el único registro de información de la compañía. Lanza 404 si no existe."""
    company_info = session.exec(select(InformationCompany)).first()
    if not company_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Information Company record not found. Please create it first (POST)."
        )
    return company_info


# --- ENDPOINT 1: OBTENER INFORMACIÓN (GET /api/company) ---

@router.get("", response_model=InformationCompanyRead, summary="Obtener la información única de la empresa")
def read_company_info(session: SessionDep):
    """
    Recupera el único registro de información de la compañía.
    """
    try:
        return get_current_company_info(session)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al leer la información de la empresa: {str(e)}",
        )


# --- ENDPOINT 2: CREAR INFORMACIÓN INICIAL (POST /api/company) ---

@router.post("", response_model=InformationCompanyRead, status_code=status.HTTP_201_CREATED, summary="Crear el registro inicial de información de la empresa")
def create_company_info(company_data: InformationCompanyCreate, session: SessionDep):
    """
    Crea el registro único de información de la compañía. Solo se puede llamar una vez.
    """
    # 1. Validación: Asegurar que NO exista ya un registro
    existing_info = session.exec(select(InformationCompany)).first()
    if existing_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Information Company record already exists. Use PATCH to update."
        )

    try:
        # 2. Validación de unicidad de email (aunque el modelo lo hace, es mejor ser explícito)
        if company_data.email:
            existing_email = session.exec(select(InformationCompany).where(InformationCompany.email == company_data.email)).first()
            if existing_email:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El correo electrónico ya está registrado.")


        # 3. Creación del registro
        company_db = InformationCompany.model_validate(company_data.model_dump())
        company_db.created_at = datetime.utcnow()
        company_db.updated_at = datetime.utcnow()

        session.add(company_db)
        session.commit()
        session.refresh(company_db)
        
        return company_db

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback() 
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear la información de la empresa: {str(e)}",
        )


# --- ENDPOINT 3: ACTUALIZAR INFORMACIÓN (PATCH /api/company) ---

@router.patch("", response_model=InformationCompanyRead, summary="Actualizar la información existente de la empresa")
def update_company_info(company_data: InformationCompanyUpdate, session: SessionDep):
    """
    Actualiza el único registro de información de la compañía.
    """
    try:
        # 1. Obtener el registro existente (usa la función auxiliar)
        company_db = get_current_company_info(session)
        
        # 2. Aplicar actualización
        data_to_update = company_data.model_dump(exclude_unset=True)
        
        # Validación de unicidad para email si se está actualizando
        if "email" in data_to_update and data_to_update["email"] != company_db.email:
            existing_email = session.exec(
                select(InformationCompany).where(InformationCompany.email == data_to_update["email"])
            ).first()
            # Si se encuentra un registro con el mismo email Y no es el registro actual (aunque solo debe haber uno)
            if existing_email and existing_email.id != company_db.id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El correo electrónico ya está registrado por otra compañía.")
            
        company_db.sqlmodel_update(data_to_update)
        company_db.updated_at = datetime.utcnow()
        
        session.add(company_db)
        session.commit()
        session.refresh(company_db)
        return company_db
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar la información de la empresa: {str(e)}",
        )
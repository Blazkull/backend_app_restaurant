from datetime import datetime
from fastapi import APIRouter, status, HTTPException
from sqlmodel import select, Session 
from core.database import SessionDep
from core.security import encode_token , ACCESS_TOKEN_EXPIRE_MINUTES, verify_password
from models.users import User 
from models.roles import Role 
from schemas.users_schema import UserLogin 
from models.tokens import AccessTokenResponse, Token as DBToken

router = APIRouter()


@router.post("/api/login", tags=["AUTH"], response_model=AccessTokenResponse)
def login(user_data:UserLogin, session: SessionDep):
    try:
        statement = select(User, Role.name).join(Role, User.id_role == Role.id).where(User.username == user_data.username)
        result = session.exec(statement).first()
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        
        user_db, role_name = result
        
        if not verify_password(user_data.password, user_db.password):
            raise HTTPException(status_code=400,detail="Invalid credentials")
        
        # --- LÓGICA DE INVALIDACIÓN Y CREACIÓN DE TOKEN ----
        
        # invalidar tokens existentes
        existing_tokens = session.exec(
            select(DBToken).where(DBToken.user_id == user_db.id, DBToken.status_token == True)
        ).all()
        for token_entry in existing_tokens:
            token_entry.status_token = False
            session.add(token_entry)
        session.commit()

        #Crea un nuevo token + rol
        payload = {
            "username": user_db.username, 
            "email": user_db.email,
            "user_id": user_db.id,
            "role_name": role_name 
        }
        encoded_jwt, expires_at = encode_token(payload)

        # Almacena el nuevo token en la base de datos
        new_token_db = DBToken(
            token=encoded_jwt,
            user_id=user_db.id,
            expiration=expires_at,
            status_token=True,
            date_token=datetime.utcnow()
        )
        session.add(new_token_db)
        session.commit()
        session.refresh(new_token_db)

        # Puedes incluir el rol en la respuesta si lo deseas
        return {
            "acces_token": encoded_jwt, 
            "token_type": "bearer",
            "role_name": role_name 
        }
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during login: {str(e)}",
        )
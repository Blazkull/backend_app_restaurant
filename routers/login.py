from datetime import datetime
from fastapi import APIRouter, status, HTTPException
from sqlmodel import select
from core.database import SessionDep
from core.security import encode_token , ACCESS_TOKEN_EXPIRE_MINUTES, verify_password
from schemas.users_schema import UserLogin
from models.users import User
from models.tokens import Token as DBToken
from schemas.tokens_schema import AccessTokenResponse

router = APIRouter()


@router.post("/api/login", tags=["AUTH"], response_model=AccessTokenResponse)
def login(user_data:UserLogin,session: SessionDep):
    try:
        user_db = session.exec(select(User).where(User.username == user_data.username)).first()

        if not user_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        
        #verificador de clave
        if not verify_password(user_data.password, user_db.password):
            raise HTTPException(status_code=400,detail="Invalid credentials")
        
        # invalidar tokens y crear uno nuevo
        existing_tokens = session.exec(
            select(DBToken).where(DBToken.user_id == user_db.id, DBToken.status_token == True)
        ).all()
        for token_entry in existing_tokens:
            token_entry.status_token = False
            session.add(token_entry)
        session.commit() # Guarda los cambios de invalidación

        # Crea un nuevo token 
        encoded_jwt, expires_at = encode_token({"username": user_data.username, "email": user_db.email})

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

        return {"acces_token": encoded_jwt, "token_type": "bearer"} 
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during login: {str(e)}",
        )
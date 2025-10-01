from datetime import datetime, timedelta
from sqlmodel import select, Session # <- Se agregó 'Session' y se eliminará SessionDep
from core.database import get_session # <- Se importa solo el generador de sesión
from models.users import User
from typing import Annotated
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from fastapi.exceptions import HTTPException
from models.tokens import Token as DBToken

from jose import JWTError, jwt
import bcrypt

from dotenv import load_dotenv
import os

load_dotenv()
SECRET_KEY= os.getenv('SECRET_KEY')
ALGORITHM= os.getenv('ALGORITHM')
# Se asume que esta variable está en .env
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', 30)) 

#instancia de una clase
outh2_scheme= OAuth2PasswordBearer(tokenUrl="token")

def hash_password(password: str) -> str:
    #Hasheao con bcrypt
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed_password.decode('utf-8') # Decodifica a string para guardar en la DB

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        # bcrypt.checkpw verifica si la contraseña plana coincide con la hasheada
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ValueError:
        return False

def encode_token(data:dict):
    to_encode = data.copy()
    # Usar datetime.now(timezone.utc) es preferible, pero mantengo utcnow() por consistencia con tu código
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token, expire # Retorna el token y la fecha de expiración
    
# FUNCIÓN CORREGIDA: Usa la anotación explícita para Session para evitar importar SessionDep
def decode_token(
    token: Annotated[str, Depends(outh2_scheme)], 
    session: Annotated[Session, Depends(get_session)] # <- ¡CORRECCIÓN CLAVE!
):
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = data.get('username')
        # print (username) # Descomentar para depurar
        if username is None:
            raise HTTPException(status_code=400, detail="The token data is incomplete")
        
        user_db = session.exec(select(User).where(User.username == username)).first()
        
        if user_db is None:
            raise HTTPException(status_code=404, detail="user not found")
        if not user_db.active:
            raise HTTPException(status_code=403, detail="User disabled. Please, contact your system manager") 
        
        #Comprobar si el token está activo en la base de datos
        db_token = session.exec(
            select(DBToken)
            .where(DBToken.token == token, DBToken.user_id == user_db.id, DBToken.status_token == True)
        ).first()

        if not db_token:
            raise HTTPException(status_code=401, detail="Token has been invalidated or not found in database.")
        
        return user_db # Retornar el usuario si el token es válido y activo

    except JWTError: #recoleccion de errores especificos
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        # Para evitar exponer detalles internos en producción, considera cambiar el 500
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
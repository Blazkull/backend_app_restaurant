
from typing import Annotated
from fastapi import Depends
from sqlmodel import SQLModel, create_engine, Session
from core.config import settings

engine = create_engine(settings.DATABASE_URL, echo=True)

#def create_db_and_tables():
#    from models.user import User
#    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]
from sqlmodel import SQLModel, Field

# Schema para la actualización masiva del estado de los permisos (el endpoint de checkboxes)
class RoleViewUpdateStatus(SQLModel):
    id_view: int = Field(description="ID de la vista cuyo estado de permiso se actualizará.")
    enabled: bool = Field(description="Nuevo estado del permiso (True para habilitar, False para deshabilitar).")

# Schema para lectura (usado dentro de RoleRead)
class RoleViewRead(SQLModel):
    id_view: int
    enabled: bool
    
    class Config:
        from_attributes = True
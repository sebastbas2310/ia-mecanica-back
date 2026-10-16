from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from services.auth_service import AuthService

router = APIRouter()
auth_service = AuthService()

# Esquema para validar que el cliente envíe el formato correcto
class LoginSchema(BaseModel):
    email: EmailStr
    password: str

@router.post("/login")
def login(credentials: LoginSchema):
    try:
        # El controller le delega la tarea pesada al Service
        resultado = auth_service.login_usuario(
            email=credentials.email,
            password=credentials.password
        )
        return {
            "mensaje": "Inicio de sesión exitoso",
            "data": resultado
        }
    except ValueError as err:
        # El controller decide qué respuesta HTTP enviar si algo falla
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(err)
        )
from fastapi import APIRouter, HTTPException, Header, status
from pydantic import BaseModel, EmailStr

from services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
service = AuthService()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest):
    try:
        return service.register(data.email, data.password)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/login")
def login(data: LoginRequest):
    try:
        return service.login(data.email, data.password)
    except Exception:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")


@router.post("/logout")
def logout(authorization: str = Header(...)):
    try:
        return service.logout(authorization)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
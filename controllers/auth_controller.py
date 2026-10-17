"""Controlador HTTP de autenticación: valida entrada, llama al servicio y traduce errores."""
from fastapi import APIRouter, Depends, HTTPException, status

from app.security import CurrentUser, get_current_user
from schemas import (
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserOut,
)
from services.auth_service import AuthService, AuthServiceError

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service() -> AuthService:
    # Inyección de dependencias: en los tests se reemplaza por un doble (mock).
    return AuthService()


def _http_error(err: AuthServiceError) -> HTTPException:
    headers = {"WWW-Authenticate": "Bearer"} if err.status_code == 401 else None
    return HTTPException(status_code=err.status_code, detail=err.message, headers=headers)


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, service: AuthService = Depends(get_auth_service)):
    try:
        needs_confirmation, session = service.register(body.email, body.password)
    except AuthServiceError as err:
        raise _http_error(err)
    msg = (
        "Usuario registrado. Revisa tu correo para confirmar la cuenta."
        if needs_confirmation
        else "Usuario registrado e inicio de sesión exitoso."
    )
    return RegisterResponse(message=msg, requires_email_confirmation=needs_confirmation, session=session)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, service: AuthService = Depends(get_auth_service)):
    try:
        return service.login(body.email, body.password)
    except AuthServiceError as err:
        raise _http_error(err)


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, service: AuthService = Depends(get_auth_service)):
    try:
        return service.refresh(body.refresh_token)
    except AuthServiceError as err:
        raise _http_error(err)


@router.post("/logout", response_model=MessageResponse)
def logout(
    user: CurrentUser = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    try:
        service.logout(user.access_token)
    except AuthServiceError as err:
        raise _http_error(err)
    return MessageResponse(message="Sesión cerrada")


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser = Depends(get_current_user)):
    return UserOut(id=user.id, email=user.email, role=user.role)

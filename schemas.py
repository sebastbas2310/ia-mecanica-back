"""DTOs (Data Transfer Objects): contratos de entrada/salida de la API validados con Pydantic."""
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)  # bcrypt usa como máximo 72 bytes


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class UserOut(BaseModel):
    id: str
    email: str | None = None
    role: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int          # segundos de vida del access token
    expires_at: int | None   # epoch (s) en que expira
    user: UserOut


class RegisterResponse(BaseModel):
    message: str
    requires_email_confirmation: bool
    session: TokenResponse | None = None


class MessageResponse(BaseModel):
    message: str

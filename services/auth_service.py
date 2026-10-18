"""Capa de servicio: lógica de autenticación contra Supabase Auth (GoTrue).

El servicio NO conoce HTTP/FastAPI: lanza AuthServiceError con un status sugerido y el
controlador decide la respuesta. Así la lógica es reutilizable y fácil de probar.
"""
import logging
from collections.abc import Callable
from typing import TypeVar

import httpx
from supabase import AuthApiError, AuthError

from schemas import TokenResponse, UserOut
from supabase_client import get_auth_client

logger = logging.getLogger(__name__)


class AuthServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400, code: str | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


# Traducción de los códigos de error de Supabase a códigos HTTP + mensajes en español.
_ERROR_MAP: dict[str, tuple[int, str]] = {
    "invalid_credentials": (401, "Correo o contraseña incorrectos"),
    "email_not_confirmed": (403, "Debes confirmar tu correo antes de iniciar sesión"),
    "user_already_exists": (409, "Ya existe un usuario con ese correo"),
    "email_exists": (409, "Ya existe un usuario con ese correo"),
    "weak_password": (422, "La contraseña es demasiado débil"),
    "over_request_rate_limit": (429, "Demasiados intentos, espera un momento"),
    "over_email_send_rate_limit": (429, "Demasiados correos enviados, espera un momento"),
    "refresh_token_not_found": (401, "Sesión inválida, inicia sesión de nuevo"),
    "refresh_token_already_used": (401, "Sesión expirada, inicia sesión de nuevo"),
    "session_not_found": (401, "Sesión no encontrada"),
}


def _to_service_error(err: AuthError) -> AuthServiceError:
    code = getattr(err, "code", None)
    if code in _ERROR_MAP:
        status, msg = _ERROR_MAP[code]
        return AuthServiceError(msg, status, code)
    status = getattr(err, "status", 400) if isinstance(err, AuthApiError) else 400
    # No filtramos detalles internos al cliente; quedan en el log.
    logger.warning("Error de Supabase Auth no mapeado: code=%s status=%s msg=%s", code, status, err)
    return AuthServiceError("No se pudo completar la autenticación", status if status >= 400 else 400, code)


T = TypeVar("T")


def _call_supabase(fn: Callable[[], T]) -> T:
    """Ejecuta una llamada a Supabase traduciendo TODOS los fallos a AuthServiceError.

    - AuthError: Supabase respondió con un error de negocio (credenciales, usuario existente...).
    - httpx.HTTPError: no hubo respuesta (URL mal configurada, sin internet, DNS, timeout) -> 503.
    - RuntimeError: configuración faltante (.env) -> 500 con mensaje claro en el log.
    """
    try:
        return fn()
    except AuthError as err:
        raise _to_service_error(err) from err
    except httpx.HTTPError as err:
        logger.error("No se pudo contactar a Supabase (%s): %s", type(err).__name__, err)
        raise AuthServiceError("No se pudo contactar al servicio de autenticación", 503) from err
    except RuntimeError as err:
        logger.error("Configuración inválida: %s", err)
        raise AuthServiceError("El servidor no está configurado correctamente", 500) from err


def _session_to_tokens(session, user) -> TokenResponse:
    return TokenResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_in=session.expires_in,
        expires_at=session.expires_at,
        user=UserOut(id=str(user.id), email=user.email, role=getattr(user, "role", None)),
    )


class AuthService:
    def register(self, email: str, password: str) -> tuple[bool, TokenResponse | None]:
        """Crea el usuario. Devuelve (requiere_confirmacion, tokens_si_hay_sesion)."""
        res = _call_supabase(
            lambda: get_auth_client().auth.sign_up({"email": email, "password": password})
        )

        if res.user is None:
            raise AuthServiceError("No se pudo registrar el usuario", 400)
        # Con "Confirm email" activado, Supabase no devuelve sesión hasta confirmar el correo.
        if res.session is None:
            return True, None
        return False, _session_to_tokens(res.session, res.user)

    def login(self, email: str, password: str) -> TokenResponse:
        res = _call_supabase(
            lambda: get_auth_client().auth.sign_in_with_password({"email": email, "password": password})
        )
        if res.session is None or res.user is None:
            raise AuthServiceError("Correo o contraseña incorrectos", 401, "invalid_credentials")
        return _session_to_tokens(res.session, res.user)

    def refresh(self, refresh_token: str) -> TokenResponse:
        """Intercambia un refresh token (de un solo uso) por un nuevo par de tokens."""
        res = _call_supabase(lambda: get_auth_client().auth.refresh_session(refresh_token))
        if res.session is None or res.user is None:
            raise AuthServiceError("Sesión inválida, inicia sesión de nuevo", 401)
        return _session_to_tokens(res.session, res.user)

    def logout(self, access_token: str, scope: str = "local") -> None:
        """Revoca en Supabase los refresh tokens de la sesión.

        scope="local" cierra solo esta sesión; "global" cierra todas las del usuario.
        Ojo: el access token (JWT) sigue siendo válido criptográficamente hasta su `exp`;
        por eso conviene que su vida sea corta (por defecto 1 h en Supabase).
        """
        try:
            _call_supabase(lambda: get_auth_client().auth.admin.sign_out(access_token, scope))
        except AuthServiceError as err:
            # Si la sesión ya no existe, el resultado deseado (sesión cerrada) ya se cumple.
            if err.code in ("session_not_found", "refresh_token_not_found"):
                return
            raise

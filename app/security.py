"""Verificación de JWT de Supabase y dependencia `get_current_user` para proteger endpoints.

Flujo por petición:
  1. Leer `Authorization: Bearer <token>`.
  2. Mirar el header del JWT para saber el algoritmo (sin confiar aún en el contenido).
  3. Obtener la clave: JWKS público (ES256/RS256) o secreto compartido (HS256 legacy).
  4. Verificar firma + exp + aud + iss. Si todo pasa, el `sub` es el id del usuario.
La verificación es local (no hay llamada de red a Supabase por petición, salvo la
descarga cacheada del JWKS), por eso escala bien.
"""
import logging
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

logger = logging.getLogger(__name__)

# auto_error=False para devolver nuestro propio 401 (FastAPI por defecto devuelve 403).
bearer_scheme = HTTPBearer(auto_error=False, description="Access token de Supabase")

# Lista blanca de algoritmos: nunca aceptar "none" ni dejar que el token elija libremente.
ASYMMETRIC_ALGS = {"ES256", "RS256"}
SYMMETRIC_ALGS = {"HS256"}


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str | None
    role: str | None
    access_token: str = field(repr=False)  # repr=False: no imprimir el token en logs
    claims: dict[str, Any] = field(default_factory=dict, repr=False)


@lru_cache
def _jwks_client() -> jwt.PyJWKClient:
    # Cachea las claves públicas en memoria; las vuelve a pedir si aparece un `kid` nuevo
    # (rotación de claves) o pasado `lifespan` segundos.
    return jwt.PyJWKClient(settings.jwks_url, cache_keys=True, lifespan=600)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _resolve_key(token: str, alg: str):
    if alg in ASYMMETRIC_ALGS:
        try:
            return _jwks_client().get_signing_key_from_jwt(token).key
        except jwt.PyJWKClientConnectionError as err:
            logger.error("No se pudo descargar el JWKS de Supabase: %s", err)
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Servicio de autenticación no disponible")
        except jwt.PyJWKClientError as err:
            raise _unauthorized("Token inválido") from err
    if alg in SYMMETRIC_ALGS:
        if not settings.supabase_jwt_secret:
            logger.error("Llegó un token HS256 pero SUPABASE_JWT_SECRET no está configurado")
            raise _unauthorized("Token inválido")
        return settings.supabase_jwt_secret
    raise _unauthorized("Algoritmo de firma no permitido")


def verify_token(token: str) -> dict[str, Any]:
    """Valida el JWT y devuelve sus claims. Lanza HTTPException 401 si algo falla."""
    try:
        header = jwt.get_unverified_header(token)
    except jwt.DecodeError as err:
        raise _unauthorized("Token mal formado") from err

    alg = header.get("alg", "")
    key = _resolve_key(token, alg)
    try:
        return jwt.decode(
            token,
            key,
            algorithms=[alg],  # solo el algoritmo ya validado contra la lista blanca
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "sub", "aud", "iss"]},
            leeway=10,  # tolerancia (s) a desfases de reloj entre servidores
        )
    except jwt.ExpiredSignatureError as err:
        raise _unauthorized("Token expirado") from err
    except jwt.InvalidTokenError as err:
        raise _unauthorized("Token inválido") from err


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    """Dependencia de FastAPI. Úsala en cualquier endpoint o router que deba estar protegido."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized("No autenticado")
    claims = verify_token(credentials.credentials)
    if claims.get("role") != "authenticated":
        # Ej.: la anon key también es un JWT válido de Supabase, pero NO representa a un usuario.
        raise _unauthorized("Se requiere un usuario autenticado")
    return CurrentUser(
        id=claims["sub"],
        email=claims.get("email"),
        role=claims.get("role"),
        access_token=credentials.credentials,
        claims=claims,
    )

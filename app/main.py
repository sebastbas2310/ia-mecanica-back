"""Punto de entrada de la API.

Regla de seguridad: los ÚNICOS endpoints públicos son /health y /auth/{register,login,refresh}.
Todo router de negocio (agente, documentos, historial) se registra en `protected`,
que exige un JWT válido en TODAS sus rutas. Así no se puede "olvidar" proteger un endpoint.
"""
import logging

from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.security import CurrentUser, get_current_user
from controllers.auth_controller import router as auth_router
from controllers.chat_controller import router as chat_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")

# Verificación temprana de configuración: mejor un aviso claro al arrancar que un 500 misterioso.
if not settings.supabase_url or "TU-PROYECTO" in settings.supabase_url:
    logger.warning("SUPABASE_URL no está configurada en .env (valor actual: %r)", settings.supabase_url)
if not settings.supabase_anon_key or settings.supabase_anon_key.startswith("tu-"):
    logger.warning("SUPABASE_ANON_KEY no está configurada en .env")

app = FastAPI(title="IA Mecánica API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,  # lista explícita, nunca "*" en producción
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health", tags=["infra"])
def health():
    return {"status": "ok"}


app.include_router(auth_router)

# --- Rutas protegidas -------------------------------------------------------
protected = APIRouter(dependencies=[Depends(get_current_user)])


@protected.get("/protected/ping", tags=["infra"])
def ping(user: CurrentUser = Depends(get_current_user)):
    """Endpoint de prueba para verificar que el token funciona."""
    return {"message": f"Hola {user.email}, tu token es válido", "user_id": user.id}


# Cuando existan, regístralos aquí y quedarán protegidos automáticamente:
# from controllers.agent_controller import router as agent_router
# from controllers.document_controller import router as document_router
# protected.include_router(agent_router)
# protected.include_router(document_router)

# Routers de negocio: todos requieren autenticación
    protected.include_router(chat_router)

app.include_router(protected)
"""Fábrica de clientes de Supabase.

IMPORTANTE: el cliente de supabase-py guarda la sesión del último usuario que hizo login
DENTRO del objeto. En un servidor que atiende a muchos usuarios a la vez, un cliente global
compartido mezclaría sesiones (condición de carrera). Por eso creamos un cliente nuevo,
sin persistencia ni auto-refresh, para cada operación de autenticación.
"""
from supabase import Client, ClientOptions, create_client

from app.config import settings


def get_auth_client() -> Client:
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise RuntimeError("Faltan SUPABASE_URL o SUPABASE_ANON_KEY en el .env")
    return create_client(
        settings.supabase_url,
        settings.supabase_anon_key,
        options=ClientOptions(auto_refresh_token=False, persist_session=False),
    )


def get_user_client(access_token: str) -> Client:
    """Create a PostgREST client whose requests run under the authenticated user's JWT."""
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise RuntimeError("Faltan SUPABASE_URL o SUPABASE_ANON_KEY en el .env")
    client = create_client(
        settings.supabase_url,
        settings.supabase_anon_key,
        options=ClientOptions(auto_refresh_token=False, persist_session=False),
    )
    client.postgrest.auth(access_token)
    return client

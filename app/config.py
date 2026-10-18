"""Configuración centralizada: TODO valor sensible viene de variables de entorno (.env)."""
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _split_csv(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


@dataclass(frozen=True)
class Settings:
    # URL del proyecto, p. ej. https://abcd1234.supabase.co
    supabase_url: str = os.getenv("SUPABASE_URL", "").rstrip("/")
    # Clave pública (anon / publishable). Es segura para operaciones de Auth.
    # Se acepta SUPABASE_KEY por compatibilidad con la versión anterior del proyecto.
    supabase_anon_key: str = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY", "")
    # Solo para proyectos con la clave JWT "legacy" (HS256). Los proyectos nuevos firman
    # con claves asimétricas (ES256/RS256) y se validan con el JWKS público, sin secreto.
    supabase_jwt_secret: str = os.getenv("SUPABASE_JWT_SECRET", "")
    # Supabase emite tokens con aud="authenticated" para usuarios con sesión.
    jwt_audience: str = os.getenv("JWT_AUDIENCE", "authenticated")
    # Orígenes del frontend autorizados (CORS). Separados por coma.
    cors_origins: list[str] = field(
        default_factory=lambda: _split_csv(
            os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
        )
    )
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1")

    @property
    def jwt_issuer(self) -> str:
        return f"{self.supabase_url}/auth/v1"

    @property
    def jwks_url(self) -> str:
        return f"{self.supabase_url}/auth/v1/.well-known/jwks.json"


settings = Settings()

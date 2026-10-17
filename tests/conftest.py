import os

# Variables de entorno de prueba ANTES de importar la app (la config se lee al importar).
os.environ.update(
    SUPABASE_URL="https://test.supabase.co",
    SUPABASE_ANON_KEY="anon-test-key",
    SUPABASE_JWT_SECRET="super-secret-test-key-with-at-least-32-bytes!!",
    CORS_ORIGINS="http://localhost:5173",
)

"""Pruebas de la capa de autenticación sin llamar a Supabase real.

- Los tokens se firman localmente (HS256 con secreto de prueba y ES256 con un par de claves
  generado en el test) para ejercitar la verificación real de app/security.py.
- AuthService se reemplaza con un doble usando dependency_overrides de FastAPI.
"""
import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

import app.security as security
from app.config import settings
from app.main import app
from controllers.auth_controller import get_auth_service
from schemas import TokenResponse, UserOut
from services.auth_service import AuthServiceError

client = TestClient(app)
USER_ID = "11111111-2222-3333-4444-555555555555"


def make_claims(**overrides):
    now = int(time.time())
    claims = {
        "sub": USER_ID,
        "email": "ana@eia.edu.co",
        "role": "authenticated",
        "aud": "authenticated",
        "iss": settings.jwt_issuer,
        "iat": now,
        "exp": now + 3600,
    }
    claims.update(overrides)
    return claims


def hs256_token(**overrides):
    return jwt.encode(make_claims(**overrides), settings.supabase_jwt_secret, algorithm="HS256")


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---------- Verificación del JWT ----------

def test_public_health():
    assert client.get("/health").status_code == 200


def test_cors_preflight_from_frontend_dev_origin():
    response = client.options(
        "/auth/login",
        headers={
            "Origin": "http://127.0.0.1:8081",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:8081"


def test_protected_without_token_is_401():
    r = client.get("/protected/ping")
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"


def test_protected_with_valid_hs256_token():
    r = client.get("/protected/ping", headers=auth(hs256_token()))
    assert r.status_code == 200
    assert r.json()["user_id"] == USER_ID


def test_me_returns_user():
    r = client.get("/auth/me", headers=auth(hs256_token()))
    assert r.json() == {"id": USER_ID, "email": "ana@eia.edu.co", "role": "authenticated"}


@pytest.mark.parametrize(
    "token, detail",
    [
        (hs256_token(exp=int(time.time()) - 3600), "Token expirado"),
        (hs256_token(aud="otra-app"), "Token inválido"),
        (hs256_token(iss="https://atacante.com/auth/v1"), "Token inválido"),
        (jwt.encode(make_claims(), "clave-incorrecta-de-32-bytes-minimo!!", algorithm="HS256"), "Token inválido"),
        ("esto.no.es-un-jwt", "Token mal formado"),
    ],
)
def test_rejects_bad_tokens(token, detail):
    r = client.get("/protected/ping", headers=auth(token))
    assert r.status_code == 401
    assert r.json()["detail"] == detail


def test_rejects_alg_none():
    token = jwt.encode(make_claims(), key=None, algorithm="none")
    r = client.get("/protected/ping", headers=auth(token))
    assert r.status_code == 401
    assert r.json()["detail"] == "Algoritmo de firma no permitido"


def test_rejects_anon_role():
    r = client.get("/protected/ping", headers=auth(hs256_token(role="anon")))
    assert r.status_code == 401


def test_tampered_payload_is_rejected():
    header, _, signature = hs256_token().split(".")
    fake_payload = jwt.utils.base64url_encode(
        jwt.api_jws.json.dumps(make_claims(sub="otro-usuario")).encode()
    ).decode()
    r = client.get("/protected/ping", headers=auth(f"{header}.{fake_payload}.{signature}"))
    assert r.status_code == 401


def test_valid_es256_token_via_jwks(monkeypatch):
    private_key = ec.generate_private_key(ec.SECP256R1())
    token = jwt.encode(make_claims(), private_key, algorithm="ES256", headers={"kid": "k1"})

    class FakeJWKS:
        def get_signing_key_from_jwt(self, _token):
            return SimpleNamespace(key=private_key.public_key())

    monkeypatch.setattr(security, "_jwks_client", lambda: FakeJWKS())
    r = client.get("/protected/ping", headers=auth(token))
    assert r.status_code == 200


# ---------- Endpoints de auth con servicio simulado ----------

TOKENS = TokenResponse(
    access_token="a", refresh_token="r", expires_in=3600, expires_at=0,
    user=UserOut(id=USER_ID, email="ana@eia.edu.co", role="authenticated"),
)


class FakeService:
    logged_out = None

    def register(self, email, password):
        if email == "ya@existe.com":
            raise AuthServiceError("Ya existe un usuario con ese correo", 409)
        return True, None

    def login(self, email, password):
        if password != "correcta123":
            raise AuthServiceError("Correo o contraseña incorrectos", 401)
        return TOKENS

    def refresh(self, refresh_token):
        if refresh_token != "r":
            raise AuthServiceError("Sesión inválida, inicia sesión de nuevo", 401)
        return TOKENS

    def logout(self, access_token, scope="local"):
        FakeService.logged_out = access_token


@pytest.fixture(autouse=True)
def fake_service():
    app.dependency_overrides[get_auth_service] = FakeService
    yield
    app.dependency_overrides.clear()


def test_register_requires_confirmation():
    r = client.post("/auth/register", json={"email": "nuevo@eia.edu.co", "password": "12345678"})
    assert r.status_code == 201
    assert r.json()["requires_email_confirmation"] is True


def test_register_conflict():
    r = client.post("/auth/register", json={"email": "ya@existe.com", "password": "12345678"})
    assert r.status_code == 409


def test_register_validation():
    r = client.post("/auth/register", json={"email": "no-es-correo", "password": "123"})
    assert r.status_code == 422


def test_login_ok_and_bad():
    ok = client.post("/auth/login", json={"email": "ana@eia.edu.co", "password": "correcta123"})
    assert ok.status_code == 200 and ok.json()["access_token"] == "a"
    bad = client.post("/auth/login", json={"email": "ana@eia.edu.co", "password": "mala"})
    assert bad.status_code == 401


def test_refresh():
    assert client.post("/auth/refresh", json={"refresh_token": "r"}).status_code == 200
    assert client.post("/auth/refresh", json={"refresh_token": "x"}).status_code == 401


def test_logout_requires_token_and_revokes():
    assert client.post("/auth/logout").status_code == 401
    token = hs256_token()
    r = client.post("/auth/logout", headers=auth(token))
    assert r.status_code == 200
    assert FakeService.logged_out == token


def test_supabase_error_mapping():
    from supabase import AuthApiError
    from services.auth_service import _to_service_error

    e = _to_service_error(AuthApiError("Invalid login credentials", 400, "invalid_credentials"))
    assert (e.status_code, e.message) == (401, "Correo o contraseña incorrectos")
    e = _to_service_error(AuthApiError("boom", 500, "unexpected_failure"))
    assert e.status_code == 500 and "boom" not in e.message


def test_supabase_unreachable_returns_503(monkeypatch):
    import httpx
    import services.auth_service as svc

    class Boom:
        class auth:
            @staticmethod
            def sign_in_with_password(_):
                raise httpx.ConnectError("getaddrinfo failed")

    monkeypatch.setattr(svc, "get_auth_client", lambda: Boom())
    app.dependency_overrides.clear()  # usar el AuthService real
    r = client.post("/auth/login", json={"email": "ana@eia.edu.co", "password": "x"})
    assert r.status_code == 503
    assert r.json()["detail"] == "No se pudo contactar al servicio de autenticación"

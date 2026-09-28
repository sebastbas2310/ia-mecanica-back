# main.py
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from supabase_client import supabase
from schemas import RegisterRequest, LoginRequest

app = FastAPI()

# CORS para que tu frontend pueda llamar a la API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en producción, especifica tu dominio
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/auth/register")
def register(data: RegisterRequest):
    try:
        response = supabase.auth.sign_up({
            "email": data.email,
            "password": data.password,
        })
        return {
            "user": response.user,
            "session": response.session,
            "message": "Revisa tu correo para confirmar la cuenta (si tienes confirmación activada)."
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/auth/login")
def login(data: LoginRequest):
    try:
        response = supabase.auth.sign_in_with_password({
            "email": data.email,
            "password": data.password,
        })
        return {
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "user": response.user,
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")


@app.post("/auth/logout")
def logout(authorization: str = Header(...)):
    try:
        token = authorization.replace("Bearer ", "")
        supabase.auth.sign_out()
        return {"message": "Sesión cerrada"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
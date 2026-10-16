# main.py
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from supabase_client import supabase
from schemas import RegisterRequest, LoginRequest
from routes.auth_routes import app as auth_routes

app = FastAPI()

# CORS para que tu frontend pueda llamar a la API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en producción, especifica tu dominio
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes, prefix="/auth", tags=["auth"])



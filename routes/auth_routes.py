from fastapi import APIRouter

router = APIRouter()

@router.post("/login")
async def login(data: LoginRequest, service: AuthService = Depends()):
    user = service.authenticate(data.email, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    return {"message": "Login exitoso", "email": user["email"]}
from supabase_client import supabase


class AuthService:
    def register(self, email: str, password: str):
        response = supabase.auth.sign_up({
            "email": email,
            "password": password,
        })
        return {
            "user": response.user,
            "session": response.session,
            "message": "Revisa tu correo para confirmar la cuenta (si tienes confirmación activada)."
        }

    def login(self, email: str, password: str):
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password,
        })
        return {
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "user": response.user,
        }

    def logout(self, authorization: str):
        token = authorization.replace("Bearer ", "")
        supabase.auth.sign_out()
        return {"message": "Sesión cerrada"}
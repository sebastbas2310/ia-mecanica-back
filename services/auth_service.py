import supabase
from supabase import create_client, Client
from app.config import SUPABASE_URL, SUPABASE_KEY


class AuthService:
    def __init__(self):
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    def login_usuario(self, email: str, password: str):
        """Autentica al usuario contra Supabase Auth y devuelve los tokens de sesión."""
        try:
            response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            return {
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
                "user_id": response.user.id,
                "email": response.user.email
            }
        except Exception as e:
            # Capturamos cualquier error de credenciales o de red
            raise ValueError(f"Error de autenticación: {str(e)}")

    def logout_usuario(self):
        try:
            supabase.auth.sign_out()
            print("Sesión cerrada con éxito OwO")
        except Exception as e:
            print(f"Error al cerrar sesión: {e}")

    def registro_usuario(self, credentials: dict):
        try:
            response = supabase.auth.sign_up(credentials)

            user = response.user
            session = response.session

            print(f"Usuario creado con éxito uwu: {user.id}")

            if session is None:
                print("Usuario registrado exitosamente. Verifica en el correo antes de iniciar sesión UvU")
            else:
                print("Usuario registrado exitosamente OwO!!!")

        except Exception as e:
            print(f"Error al registrar usuario: {e}")


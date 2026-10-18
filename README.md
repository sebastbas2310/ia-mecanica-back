# IA Mecánica API

Backend de IA Mecánica: API REST construida con FastAPI, autenticación de usuarios
con Supabase Auth y chat mecánico con LangGraph y Ollama.

Este documento describe cómo conectar un frontend (por ejemplo, Lovable) a la API.

## URLs y documentación

- API local: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- Especificación OpenAPI JSON: `http://localhost:8000/openapi.json`
- Health check: `GET /health`

Para que un frontend publicado en Lovable pueda llamar la API, el backend debe estar
desplegado en una URL accesible desde Internet, preferiblemente HTTPS. Una aplicación
web publicada no puede acceder al `localhost` de la computadora del desarrollador.

## Configuración del backend

Requisitos: Python 3.12 o 3.13 y [uv](https://docs.astral.sh/uv/).

```powershell
uv sync
Copy-Item .env.example .env
```

Completa `.env` en la raíz del backend:

```env
SUPABASE_URL=https://TU-PROYECTO.supabase.co
SUPABASE_ANON_KEY=tu-clave-publica-de-supabase
SUPABASE_JWT_SECRET=
JWT_AUDIENCE=authenticated
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1
```

Obtén `SUPABASE_URL` y la clave pública `anon`/`publishable` en Supabase, en
**Project Settings → API**. No uses la clave `service_role` ni la incluyas en el
frontend. `SUPABASE_JWT_SECRET` solo se necesita en proyectos que firman JWT con
HS256 legacy; normalmente puede quedarse vacío.

Agrega a `CORS_ORIGINS` los orígenes exactos del preview y del sitio publicado en
Lovable, separados por comas y sin rutas. Por ejemplo:

```env
CORS_ORIGINS=http://localhost:5173,https://id-preview.ejemplo.app,https://mi-app.ejemplo.com
```

No uses `*` como origen. Reinicia el backend después de modificar `.env`.

### Crear tablas del historial en Supabase

En el dashboard de Supabase, abre **SQL Editor → New query**, copia y ejecuta el
contenido de
[`supabase/migrations/20261018030000_chat_history.sql`](./supabase/migrations/20261018030000_chat_history.sql).
La migración crea las tablas de conversaciones y mensajes, índices y políticas RLS
para que cada usuario solo pueda leer o modificar su propio historial. Debe
ejecutarse una vez en cada proyecto/entorno de Supabase antes de usar las rutas de
chat. El backend utiliza el access token del usuario y la clave pública; no requiere
ni debe recibir la clave `service_role`.

### Iniciar localmente

```powershell
uv run uvicorn app.main:app --reload
```

La API local estará en `http://localhost:8000`. Para pruebas, el navegador del
frontend debe correr en una computadora que pueda alcanzar esa dirección. Para
Lovable Cloud o usuarios externos, despliega el backend y usa su URL pública HTTPS.

### Ejecutar con Docker

El repositorio incluye un `Dockerfile` basado en Python 3.12. Desde la raíz del
proyecto, construye la imagen y ejecútala con las variables del archivo `.env`:

```powershell
docker build -t ia-mecanica .
docker run --rm --env-file .env -p 8000:8000 `
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 ia-mecanica
```

En Docker Desktop para Windows, `host.docker.internal` permite que el contenedor
alcance Ollama ejecutándose en el equipo anfitrión. En otros entornos, configura
`OLLAMA_BASE_URL` con una dirección accesible desde el contenedor. La base de datos
de Supabase y el servicio Ollama deben estar disponibles para que el chat funcione.

### Iniciar el modelo de IA

Instala Ollama en la máquina o servidor que ejecuta el backend, descarga el modelo
configurado y deja Ollama ejecutándose:

```powershell
ollama pull llama3.1
ollama list
```

El valor de `OLLAMA_MODEL` debe coincidir con el modelo descargado. Ollama debe ser
accesible desde el backend mediante `OLLAMA_BASE_URL`; no basta con que esté
instalado en la computadora del usuario del frontend. Si el backend está alojado
remotamente, también debe poder conectarse a un servidor Ollama accesible desde ese
entorno.

## Conectar desde Lovable

Proporciona a Lovable estos datos:

- URL base del backend: por ejemplo `https://api.tu-dominio.com` (sin `/` final).
- Contrato OpenAPI: `https://api.tu-dominio.com/openapi.json`.
- Rutas de autenticación: `/auth/register`, `/auth/login`, `/auth/refresh`,
  `/auth/logout`, `/auth/me`.
- Rutas del chat: `/agent/chat`, `/agent/conversations` y
  `/agent/conversations/{conversation_id}`.
- Las rutas protegidas requieren `Authorization: Bearer <access_token>`.
- Al iniciar sesión, conserva `access_token` para las llamadas protegidas y
  `refresh_token` para renovar la sesión. Nunca muestres ni registres estos tokens.

Configura la URL base como una variable de entorno del frontend, por ejemplo
`VITE_API_URL=https://api.tu-dominio.com`, usando el mecanismo de variables de
entorno de tu proyecto Lovable. No escribas tokens de usuario ni claves privadas en
el código fuente.

Prompt de partida para Lovable:

> Conecta este frontend al backend IA Mecánica usando `VITE_API_URL` como URL base y
> el contrato OpenAPI en `${VITE_API_URL}/openapi.json`. Implementa registro,
> inicio de sesión, cierre de sesión y renovación de sesión usando los endpoints
> `/auth/register`, `/auth/login`, `/auth/logout` y `/auth/refresh`. Guarda el
> `access_token` y envía `Authorization: Bearer <access_token>` en las rutas
> protegidas. Implementa el chat llamando a `POST /agent/chat`, conserva el
> `conversation_id` recibido y envíalo en los siguientes mensajes. Carga el listado
> de chats desde `GET /agent/conversations` y el historial de cada chat desde
> `GET /agent/conversations/{conversation_id}`. Maneja los estados de carga y
> errores HTTP; no simules respuestas del backend.

## Contrato de la API

Todos los cuerpos y respuestas usan JSON con `Content-Type: application/json`.

### Salud del backend

`GET /health` — público.

Respuesta `200`:

```json
{
  "status": "ok"
}
```

### Registro

`POST /auth/register` — público.

```json
{
  "email": "persona@example.com",
  "password": "UnaClaveSegura123"
}
```

La contraseña debe tener de 8 a 72 caracteres. Respuesta `201` cuando se crea la
cuenta. Si Supabase requiere confirmación de correo, `requires_email_confirmation`
será `true` y `session` será `null`; la persona debe confirmar el correo y luego
iniciar sesión.

```json
{
  "message": "Usuario registrado. Revisa tu correo para confirmar la cuenta.",
  "requires_email_confirmation": true,
  "session": null
}
```

Si la confirmación de correo está desactivada en Supabase, la respuesta puede traer
una sesión con tokens.

### Inicio de sesión

`POST /auth/login` — público.

```json
{
  "email": "persona@example.com",
  "password": "UnaClaveSegura123"
}
```

Respuesta `200`:

```json
{
  "access_token": "<jwt>",
  "refresh_token": "<refresh-token>",
  "token_type": "bearer",
  "expires_in": 3600,
  "expires_at": 1890000000,
  "user": {
    "id": "<user-id>",
    "email": "persona@example.com",
    "role": "authenticated"
  }
}
```

Usa `access_token` para llamar rutas protegidas. No uses `refresh_token` como
credencial de acceso; solo se envía al endpoint de renovación.

### Renovación de sesión

`POST /auth/refresh` — público.

```json
{
  "refresh_token": "<refresh-token-actual>"
}
```

Respuesta `200`: mismo formato de tokens que `/auth/login`. Reemplaza ambos tokens
guardados por los nuevos; Supabase puede rotar el refresh token.

### Usuario autenticado

`GET /auth/me` - requiere `Authorization: Bearer <access_token>`.

Respuesta `200`:

```json
{
  "id": "<user-id>",
  "email": "persona@example.com",
  "role": "authenticated"
}
```

### Chat del asistente

`POST /agent/chat` - requiere `Authorization: Bearer <access_token>`.

Encabezados:

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

Primer mensaje de una conversación:

```json
{
  "message": "¿Por qué se puede sobrecalentar un motor?",
  "conversation_id": null
}
```

`message` debe contener entre 1 y 4000 caracteres y no puede estar vacío.

Respuesta `200`:

```json
{
  "answer": "Una causa común es un nivel bajo de refrigerante...",
  "conversation_id": "a8e48542-1c5d-4c69-8ab2-8b4bc3e52486"
}
```

La conversación y sus mensajes se guardan en Supabase. Para continuar, envía el
`conversation_id` recibido con el próximo mensaje:

```json
{
  "message": "¿Qué debería revisar primero?",
  "conversation_id": "a8e48542-1c5d-4c69-8ab2-8b4bc3e52486"
}
```

El contexto enviado al modelo incluye hasta los últimos 20 mensajes de esa
conversación. El historial persistido no se pierde al reiniciar el backend y se
comparte entre sus instancias. El asistente está orientado a procesos mecánicos y
eléctricos de carros y motos. La respuesta depende del modelo; el prompt orienta al
modelo, pero no garantiza una clasificación perfecta del tema.

### Listar conversaciones

`GET /agent/conversations?limit=50&offset=0` - requiere `Authorization: Bearer <access_token>`.

Devuelve primero las conversaciones actualizadas más recientemente:

```json
[
  {
    "id": "a8e48542-1c5d-4c69-8ab2-8b4bc3e52486",
    "title": "¿Por qué se puede sobrecalentar un motor?",
    "created_at": "2026-10-18T08:30:00Z",
    "updated_at": "2026-10-18T08:31:00Z"
  }
]
```

`limit` acepta de 1 a 100 (predeterminado 50); `offset` permite paginar desde 0.
El endpoint solo lista conversaciones del usuario autenticado.

### Recuperar el historial de una conversación

`GET /agent/conversations/{conversation_id}?limit=100&offset=0` - requiere `Authorization: Bearer <access_token>`.

Devuelve la conversación y sus mensajes ordenados cronológicamente:

```json
{
  "id": "a8e48542-1c5d-4c69-8ab2-8b4bc3e52486",
  "title": "¿Por qué se puede sobrecalentar un motor?",
  "created_at": "2026-10-18T08:30:00Z",
  "updated_at": "2026-10-18T08:31:00Z",
  "messages": [
    {
      "id": "b42d60b0-9fea-4135-9da7-67c62a02ce5f",
      "role": "user",
      "content": "¿Por qué se puede sobrecalentar un motor?",
      "created_at": "2026-10-18T08:30:00Z"
    },
    {
      "id": "46c713ba-a8d6-42d1-8bf4-8aa479c1430c",
      "role": "assistant",
      "content": "Una causa común es un nivel bajo de refrigerante...",
      "created_at": "2026-10-18T08:30:01Z"
    }
  ],
  "next_offset": null
}
```

`limit` acepta de 1 a 500 (predeterminado 100). Si `next_offset` no es `null`,
solicita la siguiente página usando ese valor como `offset`. Una conversación
inexistente o perteneciente a otro usuario responde `404`.

### Cierre de sesión

`POST /auth/logout` - requiere `Authorization: Bearer <access_token>`.

Respuesta `200`:

```json
{
  "message": "Sesión cerrada"
}
```

### Prueba de autenticación

`GET /protected/ping` - requiere `Authorization: Bearer <access_token>`.

## Errores y qué revisar

Las respuestas de error siguen el formato FastAPI:

```json
{
  "detail": "Descripción del error"
}
```

- `401`: falta el token, es inválido o expiró. Inicia sesión o renueva la sesión
  y reintenta con el nuevo `access_token`.
- `403`: la cuenta aún debe confirmar el correo.
- `422`: el cuerpo no cumple el contrato, por ejemplo falta `message`.
- `429`: Supabase limitó temporalmente registros o envíos de correo.
- `500` al autenticarse: verifica `SUPABASE_URL` y `SUPABASE_ANON_KEY` en `.env`.
- `503` en `/agent/chat`: verifica que Ollama esté activo, que tenga el modelo
  descargado y que `OLLAMA_BASE_URL`/`OLLAMA_MODEL` sean correctos.
- `503` al consultar el chat: confirma que ejecutaste la migración SQL y revisa
  que las tablas y políticas RLS existan en el proyecto Supabase configurado.
- Error CORS en el navegador: agrega el origen exacto del frontend a
  `CORS_ORIGINS` del backend y reinicia el servicio.

No publiques `.env`, tokens, contraseñas ni claves de Supabase en Lovable, GitHub,
capturas o mensajes.

## Pruebas del backend

```powershell
uv run pytest
```

# Reglas de Proyecto — `perretes-tiernos-api`

## 1. Principios Arquitectónicos Obligatorios
- **Monolito modular en FastAPI**: Separación estricta por dominio dentro de `app/modules/<dominio>/` con `models.py`, `schemas.py`, `repository.py`, `service.py`, `permissions.py` y `router.py`.
- **Cero lógica de negocio en routers**: Los routers de FastAPI solo gestionan entrada/salida HTTP, validación de esquemas y dependencias.
- **Base de datos PostgreSQL en Supabase**:
  - Conectada desde Railway vía `asyncpg` con soporte para el Transaction Pooler (`6543`).
  - Alembic gestiona exclusivamente el esquema `public`, filtrando los esquemas internos de Supabase (`auth`, `storage`, `realtime`, `vault`, etc.).
  - Sin uso de contenedores ni extensiones PostGIS de Railway; la geolocalización utiliza columnas nativas `latitude` y `longitude` (`DOUBLE PRECISION`) indexadas y cálculo Haversine.
- **Sin Docker y sin ejecución local**: Railway es el único entorno de ejecución del backend (`uvicorn app.main:app --host 0.0.0.0 --port $PORT`). No crear `Dockerfile` ni `docker-compose.yml`.

## 2. Mantenimiento de `openapi.json`
- **Actualización obligatoria**: Cada vez que se añadan, modifiquen o eliminen endpoints (`router.py`), parámetros o esquemas Pydantic (`schemas.py`), **se debe actualizar [`openapi.json`](./openapi.json)** en la raíz del proyecto para mantener el contrato OpenAPI sincronizado con los generadores de clientes TypeScript.
- El script [`scripts/generate_openapi.py`](./scripts/generate_openapi.py) exporta automáticamente la especificación y el workflow de GitHub Actions verifica que no haya desfase.


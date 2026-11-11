# Perretes Tiernos API 🐾

Backend modular para la plataforma digital de bienestar animal (**Red Social, Adopciones, Matching, Marketplace y Reservas**).

Construido con **Python 3.13+**, **FastAPI**, **Pydantic v2**, **SQLAlchemy 2.0 (Async)**, **Alembic**, **PostgreSQL en Supabase** y **ARQ (Redis)**, diseñado para desplegarse nativamente en **Railway** sin Docker.

---

## 🏗️ Arquitectura y Estado del Roadmap

El proyecto sigue una arquitectura de **monolito modular** bajo `/api/v1/` con separación estricta entre `models.py`, `schemas.py`, `repository.py`, `service.py`, `permissions.py` y `router.py`:

- ✅ **Fase 1 (Implementada): Fundamentos**
  - Configuración tipada (`app/core/config.py`), logging estructurado JSON sin PII (`app/core/logging.py`) y gestión centralizada de errores (`app/core/exceptions.py`).
  - Conexión asíncrona a **PostgreSQL en Supabase** (`asyncpg` compatible con el Transaction Pooler en puerto `6543`) y migraciones **Alembic** aisladas en el esquema `public`.
  - Validación de tokens JWT de **Supabase Auth** (`HS256` y `JWKS`) y aprovisionamiento automático Just-In-Time (JIT) del usuario de negocio (`users`, `user_profiles`, `user_preferences`).
  - Gestión de **Organizaciones** independientes (`SHELTER`, `VETERINARY`, `INSURANCE`, `PET_STORE`, `TRAINER`, `GROOMING`, `BOARDING`, `OTHER`), **Direcciones** con búsqueda por radio Haversine (`latitude`/`longitude`), **Miembros** y matriz de permisos por rol (`OWNER`, `ADMIN`, `MANAGER`, `EDITOR`, `MEMBER`).
  - Flujo de **Verificación de organizaciones** y cola administrativa para moderadores (`MODERATOR` / `SUPERADMIN`) con trazabilidad en `audit_logs`.
- ⏳ **Fase 2**: Animales y Mascotas (`animals`, `pets`)
- ⏳ **Fase 3**: Red Social (`social`)
- ⏳ **Fase 4**: Adopciones y Matching (`adoption`, `matching`)
- ⏳ **Fase 5**: Marketplace (`marketplace`)
- ⏳ **Fase 6**: Reservas y Pagos (`booking`, `payments`)
- ⏳ **Fase 7**: Monetización (`advertising`, `subscriptions`)
- ⏳ **Fase 8**: Complementarias (`notifications`, `messaging`, `moderation`, `analytics`)

---

## 🚂 Despliegue en Railway (Sin Docker)

El proyecto utiliza `railway.toml` y `pyproject.toml` para desplegarse directamente desde GitHub en **Railway**:

- **Pre-deploy command (Migraciones controladas):**
  ```bash
  alembic upgrade head
  ```
- **Start command (API HTTP):**
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port $PORT
  ```
- **Start command (Worker ARQ opcional en servicio independiente):**
  ```bash
  arq app.workers.scheduler.WorkerSettings
  ```
- **Healthcheck:** `GET /health`

### Entornos en Railway
Configura dos entornos separados en Railway (`Development` y `Production`), cada uno con sus propias variables definidas en [`.env.example`](./.env.example) apuntando a su respectivo proyecto de **Supabase** (PostgreSQL + Auth + Storage) y servicio **Redis**.

---

## 🧪 Integración Continua (GitHub Actions)

El pipeline [`.github/workflows/ci.yml`](./.github/workflows/ci.yml) se ejecuta en cada push y pull request sin requerir ejecución local:
1. Linter con **Ruff**.
2. Validación de migraciones **Alembic** (`upgrade head` → `downgrade base` → `upgrade head`) sobre una instancia efímera de PostgreSQL 16.
3. Verificación de sincronización de [`openapi.json`](./openapi.json).
4. Ejecución de toda la suite de **Pytest** (tests unitarios y de integración de extremo a extremo).


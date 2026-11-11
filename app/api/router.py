from fastapi import APIRouter

from app.modules.animals.router import router as animals_router
from app.modules.health.router import router as health_router
from app.modules.identity.router import router as identity_router
from app.modules.moderation.router import router as moderation_router
from app.modules.organizations.router import router as organizations_router
from app.modules.pets.router import router as pets_router

api_v1_router = APIRouter()

api_v1_router.include_router(health_router)
api_v1_router.include_router(identity_router)
api_v1_router.include_router(organizations_router)
api_v1_router.include_router(animals_router)
api_v1_router.include_router(pets_router)
api_v1_router.include_router(moderation_router)

from fastapi import APIRouter

from app.api import cart, profile, rules, settings, shopping

api_router = APIRouter()
api_router.include_router(shopping.router)
api_router.include_router(cart.router)
api_router.include_router(rules.router)
api_router.include_router(settings.router)
api_router.include_router(profile.router)

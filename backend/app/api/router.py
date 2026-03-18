from fastapi import APIRouter
from app.api import shopping, cart, rules, settings

api_router = APIRouter()
api_router.include_router(shopping.router)
api_router.include_router(cart.router)
api_router.include_router(rules.router)
api_router.include_router(settings.router)

"""API endpoints for household profile management."""

from fastapi import APIRouter

from app.models.profile import HouseholdProfile
from app.services.profile_manager import ProfileManagerService

router = APIRouter(prefix="/api/profile", tags=["profile"])

_profile_manager = ProfileManagerService()


@router.get("", response_model=HouseholdProfile)
async def get_profile() -> HouseholdProfile:
    """Get the current household profile."""
    return await _profile_manager.get_profile()


@router.put("", response_model=HouseholdProfile)
async def update_profile(profile: HouseholdProfile) -> HouseholdProfile:
    """Update the household profile."""
    return await _profile_manager.save_profile(profile)

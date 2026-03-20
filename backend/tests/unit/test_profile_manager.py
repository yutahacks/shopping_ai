"""Unit tests for ProfileManagerService."""

from pathlib import Path

import pytest

from app.models.profile import FamilyMember, HouseholdProfile
from app.services.profile_manager import ProfileManagerService


@pytest.fixture
def tmp_profile_path(tmp_path: Path) -> Path:
    """Return a temporary path for the profile file."""
    return tmp_path / "profile.json"


@pytest.fixture
def manager(tmp_profile_path: Path) -> ProfileManagerService:
    """Create a ProfileManagerService with a temp file path."""
    return ProfileManagerService(path=tmp_profile_path)


@pytest.mark.asyncio
async def test_get_profile_returns_defaults_when_no_file(manager: ProfileManagerService) -> None:
    """Getting profile when file doesn't exist returns empty defaults."""
    profile = await manager.get_profile()
    assert profile.members == []
    assert profile.food_preferences is None
    assert profile.weekly_budget is None


@pytest.mark.asyncio
async def test_save_and_get_profile(manager: ProfileManagerService, tmp_profile_path: Path) -> None:
    """Saving and loading a profile round-trips correctly."""
    profile = HouseholdProfile(
        members=[
            FamilyMember(name="太郎", age_group="adult", allergies=["えび"]),
            FamilyMember(name="花子", age_group="child", dislikes=["ピーマン"]),
        ],
        food_preferences="和食中心",
        weekly_budget=10000,
    )
    await manager.save_profile(profile)
    assert tmp_profile_path.exists()

    loaded = await manager.get_profile()
    assert len(loaded.members) == 2
    assert loaded.members[0].name == "太郎"
    assert loaded.members[0].allergies == ["えび"]
    assert loaded.members[1].age_group == "child"
    assert loaded.food_preferences == "和食中心"
    assert loaded.weekly_budget == 10000


@pytest.mark.asyncio
async def test_to_prompt_section_empty() -> None:
    """Empty profile produces default message."""
    profile = HouseholdProfile()
    assert profile.to_prompt_section() == "世帯情報は未設定です。"


@pytest.mark.asyncio
async def test_to_prompt_section_with_members() -> None:
    """Profile with members produces formatted prompt section."""
    profile = HouseholdProfile(
        members=[
            FamilyMember(name="太郎", age_group="adult", allergies=["えび", "かに"]),
            FamilyMember(name="花子", age_group="adult"),
            FamilyMember(name="次郎", age_group="child", dislikes=["ピーマン"]),
        ],
        food_preferences="和食中心",
        weekly_budget=15000,
    )
    section = profile.to_prompt_section()
    assert "3人" in section
    assert "大人2名" in section
    assert "子供1名" in section
    assert "えび" in section
    assert "かに" in section
    assert "ピーマン" in section
    assert "和食中心" in section
    assert "15,000円" in section

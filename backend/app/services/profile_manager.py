"""Service for managing household profile persistence."""

import json
from pathlib import Path

from app.config import settings
from app.models.profile import HouseholdProfile


class ProfileManagerService:
    """Manages reading and writing of the household profile JSON file.

    The profile is stored as a JSON file at the configured profile_path.
    """

    def __init__(self, path: Path | None = None) -> None:
        """Initialize with the profile file path.

        Args:
            path: Override path for the profile file. Defaults to settings.profile_path.
        """
        self._path = path or settings.profile_path

    async def get_profile(self) -> HouseholdProfile:
        """Load the household profile from disk.

        Returns:
            The current HouseholdProfile, or a default empty profile if
            the file does not exist.
        """
        if not self._path.exists():
            return HouseholdProfile()

        import asyncio

        return await asyncio.to_thread(self._read_sync)

    async def save_profile(self, profile: HouseholdProfile) -> HouseholdProfile:
        """Save the household profile to disk.

        Args:
            profile: The profile to persist.

        Returns:
            The saved profile.
        """
        import asyncio

        await asyncio.to_thread(self._write_sync, profile)
        return profile

    def _read_sync(self) -> HouseholdProfile:
        """Read profile from JSON file synchronously."""
        data = json.loads(self._path.read_text(encoding="utf-8"))
        return HouseholdProfile.model_validate(data)

    def _write_sync(self, profile: HouseholdProfile) -> None:
        """Write profile to JSON file synchronously."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            profile.model_dump_json(indent=2, exclude_none=True),
            encoding="utf-8",
        )

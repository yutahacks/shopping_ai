"""Application configuration via environment variables."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Attributes:
        openai_api_key: OpenAI API key for the Agents SDK.
        data_dir: Base directory for persistent data files.
        database_path: Path to the SQLite database file.
        rules_path: Path to the shopping rules YAML file.
        cookies_path: Path to the Amazon cookies JSON file.
        profile_path: Path to the household profile JSON file.
        openai_model: OpenAI model identifier for plan generation.
        browser_headless: Whether to run Playwright in headless mode.
        browser_timeout_ms: Playwright navigation timeout in milliseconds.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    openai_api_key: str = ""
    data_dir: Path = Path("./data")
    config_dir: Path = Path("./config")
    database_path: Path = Path("./data/shopping.db")
    rules_path: Path = Path("./data/rules.yaml")
    cookies_path: Path = Path("./data/cookies.json")
    profile_path: Path = Path("./data/profile.json")

    # OpenAI model
    openai_model: str = "gpt-5.4-mini"

    # Security
    api_secret_key: str = ""

    # Logging
    log_level: str = "INFO"

    # Playwright
    browser_headless: bool = True
    browser_timeout_ms: int = 30000

    @property
    def data_dir_resolved(self) -> Path:
        """Return the resolved absolute path of the data directory."""
        return self.data_dir.resolve()


settings = Settings()

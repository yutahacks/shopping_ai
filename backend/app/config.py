from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    anthropic_api_key: str = ""
    data_dir: Path = Path("/data")
    database_path: Path = Path("/data/shopping.db")
    rules_path: Path = Path("/data/rules.yaml")
    cookies_path: Path = Path("/data/cookies.json")

    # Claude model
    claude_model: str = "claude-sonnet-4-6"

    # Playwright
    browser_headless: bool = True
    browser_timeout_ms: int = 30000

    @property
    def data_dir_resolved(self) -> Path:
        return self.data_dir.resolve()


settings = Settings()

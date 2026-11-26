from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    scheduler_enabled: bool = True
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    def validate_on_init(self) -> None:
        """Validate settings on initialization"""
        if len(self.secret_key) < 32:
            raise ValueError(
                "SECRET_KEY must be at least 32 characters long for security"
            )


settings = Settings()
# Trigger validation
settings.validate_on_init()

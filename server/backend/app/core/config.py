from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    # APP
    app_name: str = Field(..., validation_alias="APP_NAME")
    app_debug: bool = Field(..., validation_alias="APP_DEBUG")
    app_environment: str = Field(..., validation_alias="APP_ENVIRONMENT")
    app_version: str = Field(..., validation_alias="APP_VERSION")

    # DB
    db_host: str = Field(..., validation_alias="DB_HOST")
    db_port: int = Field(..., validation_alias="DB_PORT")
    db_name: str = Field(..., validation_alias="DB_NAME")
    db_user: str = Field(..., validation_alias="DB_USER")
    db_password: str = Field(..., validation_alias="DB_PASSWORD")

    # JWT
    jwt_secret: str = Field(..., validation_alias="JWT_SECRET")
    jwt_algorithm: str = Field("HS256", validation_alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(30, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def db_url(self) -> str:
        return (
            f"postgresql+asyncpg://"
            f"{self.db_user}:{self.db_password}@"
            f"{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()

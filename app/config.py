from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    debug: bool = False
    auth_token: str

    # This override of model_config is expected in pydantic-settings
    model_config = SettingsConfigDict(
        env_file=".env"
    )


settings = Settings()

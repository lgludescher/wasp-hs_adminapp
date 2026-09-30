from pydantic_settings import BaseSettings, SettingsConfigDict
# from typing import Optional


class Settings(BaseSettings):
    database_url: str
    debug: bool = False
    auth_token: str

    # Azure OpenAI Configuration
    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_deployment_name: str = "gpt-5.6-luna"
    # azure_openai_api_version: Optional[str] = None

    # This override of model_config is expected in pydantic-settings
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()

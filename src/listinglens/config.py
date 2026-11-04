from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "ListingLens"
    app_version: str = "0.0.1"
    app_description: str = (
        "Focuses on inspecting, understanding, and enriching marketplace listings."
    )
    debug: bool = False

    database_url: str = (
        "postgresql:+psycopg://listinglens:listinglens@localhost:5432/listinglens"
    )


settings = Settings()

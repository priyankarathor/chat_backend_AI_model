from pydantic_settings import BaseSettings, SettingsConfigDict
# all config
class Settings(BaseSettings):
    MONGODB_URL: str | None = None
    DATABASE_NAME: str | None = None

    GROQ_API_KEY: str | None = None
    GROQ_MODEL:str = "openai/gpt-oss-120b"

    JWT_SECRET_KEY: str | None = None
    JWT_ALGORITHM:str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES:int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = SettingsConfigDict(
        env_file = ".env",
        extra="ignore"
    )

settings = Settings()

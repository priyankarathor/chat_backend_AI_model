from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    MONGODB_URL:str
    DATABASE_NAME:str

    GROQ_API_KEY:str
    GROQ_MODEL:str = "openai/gpt-oss-120b"

    JWT_SECRET_KEY:str
    JWT_ALGORITHM:str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES:int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = SettingsConfigDict(
        env_file = ".env",
        extra="ignore"
    )

settings = Settings()

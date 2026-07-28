from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DB_USER: str = "root"
    DB_PASSWORD: str = "password1234"
    DB_HOST: str = "localhost"
    DB_PORT: str = "3306"
    DB_NAME: str = "ai_health"
    JWT_SECRET_KEY: str = "change-me-in-env"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REDIS_URL: str = "redis://localhost:6379/0"
    PREDICTION_QUEUE_NAME: str = "prediction:jobs"
    PREDICTION_RESULT_CHANNEL_PREFIX: str = "prediction:results"
    PREDICTION_TIMEOUT_SECONDS: float = Field(default=2.5, gt=0)

    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }


settings = Settings()


class AuthSettings(BaseSettings):
    JWT_SECRET_KEY: str = "development-only-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    # `fastapi run`의 로컬 HTTP 환경에서는 Secure 쿠키가 저장되지 않는다.
    # 실제 HTTPS 배포 환경에서는 .env에서 반드시 true로 설정한다.
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "strict"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


auth_settings = AuthSettings()

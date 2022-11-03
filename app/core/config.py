# -*- coding: utf-8 -*-
import secrets
from typing import Any, Dict, List, Optional, Union
from pydantic import AnyHttpUrl, BaseSettings, EmailStr, HttpUrl, PostgresDsn, validator


class Settings(BaseSettings):
    """
    Settings for the project.
    """

    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    # BACKEND_CORS_ORIGINS is a JSON-formatted list of origins
    # e.g: '["http://localhost", "http://localhost:4200", "http://localhost:8080"]'
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    PROJECT_NAME: str = "Base dos Dados API"
    PROJECT_DESCRIPTION: str = """
        Base dos Dados is a project to democratize access to data in Brazil. We are
        building a platform to make it easy to find, access, and analyze data from
        Brazilian public institutions. We are also building a community of data
        scientists, journalists, and other interested parties to help us build the
        platform and use it to create new knowledge.

        This API is a work in progress. We are currently working on the first version
        of the API, which will allow users to interact with the data we have already
        collected, treated and published on our public Data Lake. 💚🎲
        """
    VERSION: str = "0.0.1"
    TERMS_OF_SERVICE: str = "https://basedosdados.org/terms"
    CONTACT_URL: HttpUrl = "https://basedosdados.org/contato"
    CONTACT_EMAIL: EmailStr = "contato@basedosdados.org"
    LICENSE_NAME: str = "MIT License"
    LICENSE_URL: HttpUrl = "https://mit-license.org/"
    # TODO: Setup sentry for base dos dados project
    SENTRY_DSN: Optional[HttpUrl] = None

    @validator("SENTRY_DSN", pre=True)
    def sentry_dsn_can_be_blank(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str) and len(v) == 0:
            return None
        return v

    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    SQLALCHEMY_DATABASE_URI: Optional[PostgresDsn] = None

    @validator("SQLALCHEMY_DATABASE_URI", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
        if isinstance(v, str):
            return v
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            user=values.get("POSTGRES_USER"),
            password=values.get("POSTGRES_PASSWORD"),
            host=values.get("POSTGRES_SERVER"),
            path=f"/{values.get('POSTGRES_DB') or ''}",
        )


settings = Settings()

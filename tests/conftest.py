from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401 - register every table on Base.metadata
from app.apis import users
from app.core.db.databases import Base, async_get_db
from app.core.errors import register_exception_handlers


@pytest.fixture(scope="session")
def test_app() -> FastAPI:
    application = FastAPI()
    register_exception_handlers(application)
    application.include_router(users.router)
    return application


@pytest_asyncio.fixture
async def client(test_app: FastAPI) -> AsyncIterator[AsyncClient]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    test_app.dependency_overrides[async_get_db] = override_get_db

    transport = ASGITransport(app=test_app)
    async with AsyncClient(
        transport=transport,
        base_url="https://testserver",
    ) as test_client:
        yield test_client

    test_app.dependency_overrides.clear()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
    await engine.dispose()

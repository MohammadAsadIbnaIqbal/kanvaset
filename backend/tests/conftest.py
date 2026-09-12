import os
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from backend.app.core.config import settings

# Configure test settings
TEST_DB_FILE = "test_kanvaset.db"
settings.DATABASE_URL = f"sqlite+aiosqlite:///./{TEST_DB_FILE}"
settings.USE_REDIS = False
settings.SECRET_KEY = "test_secret_key_for_unit_tests_only_123456789"

from backend.app.core.database import Base, get_db
from backend.app.core.security import create_access_token, get_password_hash
from backend.app.main import app
from backend.app.models.user import User

test_engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

TestingSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(autouse=True)
async def init_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session():
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture
async def client():
    async def override_get_db():
        async with TestingSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db_session: AsyncSession):
    user = User(
        email="alice@example.com",
        username="alice",
        hashed_password=get_password_hash("password123"),
        avatar_url="https://api.dicebear.com/7.x/avataaars/svg?seed=alice",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_user_b(db_session: AsyncSession):
    user = User(
        email="bob@example.com",
        username="bob",
        hashed_password=get_password_hash("password123"),
        avatar_url="https://api.dicebear.com/7.x/avataaars/svg?seed=bob",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User):
    token = create_access_token(test_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_b(test_user_b: User):
    token = create_access_token(test_user_b.id)
    return {"Authorization": f"Bearer {token}"}

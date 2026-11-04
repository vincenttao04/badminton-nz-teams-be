from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlmodel import Session, SQLModel

import app.models  # noqa: F401  # registers every table on SQLModel.metadata
from app.config import get_settings
from app.db import get_session
from app.main import create_app

TEST_DB_NAME = "badminton_nz_test"


def _test_database_url() -> str:
    """Derive the test database URL from DATABASE_URL by swapping the db name."""
    base = get_settings().database_url.rsplit("/", 1)[0]
    return f"{base}/{TEST_DB_NAME}"


def _truncate_all(engine: Engine) -> None:
    """Empty every table so the next test starts from a clean database."""
    tables = ", ".join(table.name for table in SQLModel.metadata.sorted_tables)
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture(scope="session")
def engine() -> Generator[Engine, None, None]:
    test_engine = create_engine(_test_database_url())
    SQLModel.metadata.create_all(test_engine)
    yield test_engine
    SQLModel.metadata.drop_all(test_engine)
    test_engine.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
    _truncate_all(engine)


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: db_session
    with TestClient(app, base_url="https://testserver") as test_client:
        yield test_client
    app.dependency_overrides.clear()

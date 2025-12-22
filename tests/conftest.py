import asyncio
from unittest.mock import MagicMock

import pytest
from testcontainers.postgres import PostgresContainer
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_db():
    """Ephemeral Postgres for integration tests."""
    with PostgresContainer("postgres:15") as postgres:
        engine = create_engine(postgres.get_connection_url())
        Base.metadata.create_all(engine)
        yield engine


@pytest.fixture
def db_session(test_db):
    Session = sessionmaker(bind=test_db)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def mock_selenium_driver():
    driver = MagicMock()
    driver.find_elements.return_value = []
    driver.page_source = ""
    return driver

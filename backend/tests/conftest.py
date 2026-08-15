import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models
from database import get_db
from main import app


TEST_DATABASE_URL = "sqlite://"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def reset_database():
    models.Base.metadata.drop_all(bind=test_engine)
    models.Base.metadata.create_all(bind=test_engine)

    db = TestingSessionLocal()

    db.add_all(
        [
            models.Appliance(
                id="ev_charger",
                name="EV Charger",
                kw=7.2,
                interruptible=True,
                priority="low",
            ),
            models.Appliance(
                id="gaming_pc",
                name="Gaming PC",
                kw=0.5,
                interruptible=False,
                priority="medium",
            ),
            models.Appliance(
                id="refrigerator",
                name="Refrigerator",
                kw=0.15,
                interruptible=False,
                priority="critical",
            ),
            models.Appliance(
                id="space_heater",
                name="Space Heater",
                kw=1.5,
                interruptible=True,
                priority="medium",
            ),
        ]
    )
    db.commit()
    db.close()

    yield

    models.Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("EIA_API_KEY", raising=False)
    return TestClient(app)

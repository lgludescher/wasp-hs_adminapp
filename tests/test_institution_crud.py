from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from app.dependencies import get_db
from app.database import Base
from app.main import app
from app import schemas

# in-memory DB
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=test_engine
)

# create schema once
Base.metadata.create_all(bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db  # type: ignore
client = TestClient(app)


# reset before each test
@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield


def test_create_and_list_institution():
    # create
    resp = client.post(
        "/institutions/",
        json={"institution": "Uni A"},
        headers={"X-Dev-User": "alice"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["institution"] == "Uni A"
    assert isinstance(data["id"], int)

    # list
    resp = client.get("/institutions/", headers={"X-Dev-User": "alice"})
    names = [i["institution"] for i in resp.json()]
    assert "Uni A" in names


def test_read_institution():
    # seed
    resp = client.post("/institutions/", json={"institution": "Uni B"}, headers={"X-Dev-User": "alice"})
    inst_id = resp.json()["id"]

    # read
    resp = client.get(f"/institutions/{inst_id}", headers={"X-Dev-User": "alice"})
    assert resp.status_code == 200
    assert resp.json()["institution"] == "Uni B"

    # 404
    resp = client.get("/institutions/999", headers={"X-Dev-User": "alice"})
    assert resp.status_code == 404


def test_update_institution():
    # seed
    resp = client.post("/institutions/", json={"institution": "X"}, headers={"X-Dev-User": "alice"})
    inst_id = resp.json()["id"]

    # update
    resp = client.put(
        f"/institutions/{inst_id}",
        json={"institution": "Y"},
        headers={"X-Dev-User": "alice"}
    )
    assert resp.status_code == 200
    assert resp.json()["institution"] == "Y"


def test_delete_institution():
    # seed & delete
    resp = client.post("/institutions/", json={"institution": "ToRemove"}, headers={"X-Dev-User": "alice"})
    inst_id = resp.json()["id"]
    resp = client.delete(f"/institutions/{inst_id}", headers={"X-Dev-User": "alice"})
    assert resp.status_code == 204

    # confirm gone
    resp = client.get("/institutions/", headers={"X-Dev-User": "alice"})
    assert all(i["id"] != inst_id for i in resp.json())


def test_search_institution():
    # seed multiple
    client.post("/institutions/", json={"institution": "Alpha Inst"}, headers={"X-Dev-User": "alice"})
    client.post("/institutions/", json={"institution": "Beta Inst"},  headers={"X-Dev-User": "alice"})

    # substring match
    resp = client.get("/institutions?search=alpha", headers={"X-Dev-User": "alice"})
    assert resp.status_code == 200
    assert [i["institution"] for i in resp.json()] == ["Alpha Inst"]


def test_create_duplicate_institution():
    # first create succeeds
    resp1 = client.post(
        "/institutions/",
        json={"institution": "Dup Uni"},
        headers={"X-Dev-User": "alice"}
    )
    assert resp1.status_code == 200

    # second create with same name should 400
    resp2 = client.post(
        "/institutions/",
        json={"institution": "Dup Uni"},
        headers={"X-Dev-User": "alice"}
    )
    assert resp2.status_code == 400
    assert resp2.json()["detail"] == "Institution 'Dup Uni' already exists"

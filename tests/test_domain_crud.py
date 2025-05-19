from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from app.dependencies import get_db
from app.database import Base
from app.main import app

# Setup in‐memory DB
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)

# create schema once
Base.metadata.create_all(bind=test_engine)


# dependency override
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db  # type: ignore
client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield


# --- Branch tests ---
def test_create_and_list_branch():
    resp = client.post("/branches/", json={"branch":"Branch A"}, headers={"X-Dev-User":"alice"})
    assert resp.status_code == 200
    b = resp.json()
    assert b["branch"] == "Branch A"
    assert isinstance(b["id"], int)

    resp = client.get("/branches/", headers={"X-Dev-User":"alice"})
    names = [x["branch"] for x in resp.json()]
    assert "Branch A" in names


def test_read_branch():
    resp = client.post("/branches/", json={"branch":"B"}, headers={"X-Dev-User":"alice"})
    bid = resp.json()["id"]

    # existing
    resp = client.get(f"/branches/{bid}", headers={"X-Dev-User":"alice"})
    assert resp.status_code == 200
    assert resp.json()["branch"] == "B"

    # not found
    resp = client.get("/branches/999", headers={"X-Dev-User":"alice"})
    assert resp.status_code == 404


def test_update_branch():
    bid = client.post("/branches/", json={"branch":"Old"}, headers={"X-Dev-User":"alice"}).json()["id"]
    resp = client.put(f"/branches/{bid}", json={"branch":"New"}, headers={"X-Dev-User":"alice"})
    assert resp.status_code == 200
    assert resp.json()["branch"] == "New"


def test_delete_branch():
    bid = client.post("/branches/", json={"branch":"ToDel"}, headers={"X-Dev-User":"alice"}).json()["id"]
    resp = client.delete(f"/branches/{bid}", headers={"X-Dev-User":"alice"})
    assert resp.status_code == 204
    assert all(x["id"] != bid for x in client.get("/branches/", headers={"X-Dev-User":"alice"}).json())


def test_delete_branch_with_fields():
    bid = client.post("/branches/", json={"branch":"HasF"}, headers={"X-Dev-User":"alice"}).json()["id"]
    # seed a field
    client.post("/fields/", json={"field":"F1","branch_id":bid}, headers={"X-Dev-User":"alice"})
    resp = client.delete(f"/branches/{bid}", headers={"X-Dev-User":"alice"})
    assert resp.status_code == 400


def test_search_branches():
    client.post("/branches/", json={"branch":"Alpha"}, headers={"X-Dev-User":"alice"})
    client.post("/branches/", json={"branch":"Beta"},  headers={"X-Dev-User":"alice"})
    resp = client.get("/branches/?search=alp", headers={"X-Dev-User":"alice"})
    assert [x["branch"] for x in resp.json()] == ["Alpha"]


# --- Field tests ---
def test_create_and_list_field():
    bid = client.post("/branches/", json={"branch":"B1"}, headers={"X-Dev-User":"alice"}).json()["id"]
    resp = client.post("/fields/", json={"field":"F1","branch_id":bid}, headers={"X-Dev-User":"alice"})
    assert resp.status_code == 200
    f = resp.json()
    assert f["field"] == "F1" and f["branch_id"] == bid

    resp = client.get("/fields/", headers={"X-Dev-User":"alice"})
    pairs = [(x["field"], x["branch_id"]) for x in resp.json()]
    assert ("F1", bid) in pairs


def test_read_field():
    bid = client.post("/branches/", json={"branch":"B2"}, headers={"X-Dev-User":"alice"}).json()["id"]
    fid = client.post("/fields/", json={"field":"F2","branch_id":bid}, headers={"X-Dev-User":"alice"}).json()["id"]

    resp = client.get(f"/fields/{fid}", headers={"X-Dev-User":"alice"})
    assert resp.status_code == 200
    assert resp.json()["field"] == "F2"

    resp = client.get("/fields/999", headers={"X-Dev-User":"alice"})
    assert resp.status_code == 404


def test_update_field():
    bid1 = client.post("/branches/", json={"branch":"B3"}, headers={"X-Dev-User":"alice"}).json()["id"]
    bid2 = client.post("/branches/", json={"branch":"B4"}, headers={"X-Dev-User":"alice"}).json()["id"]
    fid = client.post("/fields/", json={"field":"OldF","branch_id":bid1}, headers={"X-Dev-User":"alice"}).json()["id"]

    resp = client.put(f"/fields/{fid}", json={"field":"NewF","branch_id":bid2}, headers={"X-Dev-User":"alice"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["field"] == "NewF" and data["branch_id"] == bid2


def test_delete_field():
    bid = client.post("/branches/", json={"branch":"B5"}, headers={"X-Dev-User":"alice"}).json()["id"]
    fid = client.post("/fields/", json={"field":"ToDel","branch_id":bid}, headers={"X-Dev-User":"alice"}).json()["id"]

    resp = client.delete(f"/fields/{fid}", headers={"X-Dev-User":"alice"})
    assert resp.status_code == 204
    assert all(x["id"] != fid for x in client.get("/fields/", headers={"X-Dev-User":"alice"}).json())


def test_list_fields_by_branch():
    b1 = client.post("/branches/", json={"branch":"B6"}, headers={"X-Dev-User":"alice"}).json()["id"]
    b2 = client.post("/branches/", json={"branch":"B7"}, headers={"X-Dev-User":"alice"}).json()["id"]
    client.post("/fields/", json={"field":"FX","branch_id":b1}, headers={"X-Dev-User":"alice"})
    client.post("/fields/", json={"field":"FY","branch_id":b2}, headers={"X-Dev-User":"alice"})

    resp = client.get(f"/fields/?branch_id={b1}", headers={"X-Dev-User":"alice"})
    assert [x["field"] for x in resp.json()] == ["FX"]


def test_search_fields():
    b = client.post("/branches/", json={"branch":"B8"}, headers={"X-Dev-User":"alice"}).json()["id"]
    client.post("/fields/", json={"field":"AlphaF","branch_id":b}, headers={"X-Dev-User":"alice"})
    client.post("/fields/", json={"field":"BetaF","branch_id":b}, headers={"X-Dev-User":"alice"})

    resp = client.get("/fields/?search=beta", headers={"X-Dev-User":"alice"})
    assert [x["field"] for x in resp.json()] == ["BetaF"]

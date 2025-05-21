from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from app.dependencies import get_db
from app.database import Base
from app.main import app
from app import schemas

# in-memory
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)

Base.metadata.create_all(bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# app.dependency_overrides[get_db] = lambda: next(__import__('__main__').TestingSessionLocal())  # type: ignore
app.dependency_overrides[get_db] = override_get_db  # type: ignore
client = TestClient(app)


@pytest.fixture(autouse=True)
def reset():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield


# --- CourseTerm tests ---
def test_course_term_lifecycle():
    # list empty
    assert client.get("/course-terms/", headers={"X-Dev-User": "alice"}).json() == []

    # create next twice
    t1 = client.post("/course-terms/next", headers={"X-Dev-User": "alice"}).json()
    t2 = client.post("/course-terms/next", headers={"X-Dev-User": "alice"}).json()
    assert t2["year"] >= t1["year"]

    # list
    terms = client.get("/course-terms/?active=true", headers={"X-Dev-User": "alice"}).json()
    assert len(terms) == 2

    # update deactivate first
    resp = client.put(f"/course-terms/{t1['id']}", json={"is_active": False}, headers={"X-Dev-User": "alice"})
    assert resp.json()["is_active"] is False

    # cannot delete older
    bad = client.delete(f"/course-terms/{t1['id']}", headers={"X-Dev-User": "alice"})
    assert bad.status_code == 400

    # delete only latest
    resp = client.delete(f"/course-terms/{t2['id']}", headers={"X-Dev-User": "alice"})
    assert resp.status_code == 204


# --- Course tests ---
def test_course_basic_crud_and_filters():
    # prepare term
    t1 = client.post("/course-terms/next", headers={"X-Dev-User": "alice"}).json()
    t2 = client.post("/course-terms/next", headers={"X-Dev-User": "alice"}).json()
    # create two
    c1 = client.post("/courses/", json={"title": "C1", "course_term_id": t1["id"]},
                     headers={"X-Dev-User": "alice"}).json()
    c2 = client.post("/courses/", json={"title": "C2", "course_term_id": t2["id"]},
                     headers={"X-Dev-User": "alice"}).json()

    # read
    assert client.get(f"/courses/{c1['id']}", headers={"X-Dev-User": "alice"}).status_code == 200

    # list with descending – c2 should come first
    lst = client.get("/courses/", headers={"X-Dev-User": "alice"}).json()
    assert [x["title"] for x in lst] == ["C2", "C1"]

    # filter by title
    assert client.get("/courses/?title=C1", headers={"X-Dev-User": "alice"}).json()[0]["id"] == c1["id"]

    # substring search
    client.post("/courses/", json={"title": "AlphaCourse", "course_term_id": t1["id"]}, headers={"X-Dev-User": "alice"})
    subs = client.get("/courses/?search=Alpha", headers={"X-Dev-User": "alice"}).json()
    assert subs[0]["title"] == "AlphaCourse"

    # update notes
    upd = client.put(f"/courses/{c1['id']}", json={"notes": "N1"}, headers={"X-Dev-User": "alice"}).json()
    assert upd["notes"] == "N1"

    # delete c2
    assert client.delete(f"/courses/{c2['id']}", headers={"X-Dev-User": "alice"}).status_code == 204

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from app.dependencies import get_db
from app.database import Base
from app.main import app

# in-memory SQLite
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine
)

Base.metadata.create_all(bind=test_engine)


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


HEADERS = {"X-Dev-User": "alice"}


def test_course_institutions_lifecycle():
    # prepare a term and course first
    client.post("/course-terms/next", headers=HEADERS)
    resp = client.get("/course-terms/", headers=HEADERS)
    term_id = resp.json()[0]["id"]

    c = client.post("/courses/", json={
        "title": "C1", "course_term_id": term_id
    }, headers=HEADERS).json()
    cid = c["id"]

    # initially empty
    assert client.get(f"/courses/{cid}/institutions/", headers=HEADERS).json() == []

    # add institution
    inst = client.post("/institutions/", json={"institution": "I1"}, headers=HEADERS).json()
    iid = inst["id"]
    added = client.post(f"/courses/{cid}/institutions/", json={"institution_id": iid}, headers=HEADERS).json()
    assert added["id"] == iid

    # list shows it
    lst = client.get(f"/courses/{cid}/institutions/", headers=HEADERS).json()
    assert [i["id"] for i in lst] == [iid]

    # remove it
    r = client.delete(f"/courses/{cid}/institutions/{iid}", headers=HEADERS)
    assert r.status_code == 204
    assert client.get(f"/courses/{cid}/institutions/", headers=HEADERS).json() == []


@pytest.mark.skip("people endpoints not implemented yet")
def test_course_students_lifecycle():
    # setup
    client.post("/course-terms/next", headers=HEADERS)
    term_id = client.get("/course-terms/", headers=HEADERS).json()[0]["id"]
    cid = client.post("/courses/", json={"title": "C2", "course_term_id": term_id}, headers=HEADERS).json()["id"]
    # create a person-role
    client.post("/people/", json={"first_name": "A", "last_name": "B", "email": "a@b.com"}, headers=HEADERS)
    pr = client.get("/people/", headers=HEADERS).json()[0]  # assume only one
    prid = pr["roles"][0]["id"]

    # initially none
    assert client.get(f"/courses/{cid}/students/", headers=HEADERS).json() == []

    # add
    added = client.post(f"/courses/{cid}/students/", json={
        "phd_student_id": prid,
        "is_completed": False,
        "grade": None
    }, headers=HEADERS).json()
    assert "phd_student_id" in added

    # list contains
    assert any(s["phd_student_id"] == prid for s in client.get(f"/courses/{cid}/students/", headers=HEADERS).json())

    # remove
    sid = added["id"]
    r = client.delete(f"/courses/{cid}/students/{sid}", headers=HEADERS)
    assert r.status_code == 204
    assert client.get(f"/courses/{cid}/students/", headers=HEADERS).json() == []


@pytest.mark.skip("people endpoints not implemented yet")
def test_course_teachers_lifecycle():
    # setup course
    client.post("/course-terms/next", headers=HEADERS)
    term_id = client.get("/course-terms/", headers=HEADERS).json()[0]["id"]
    cid = client.post("/courses/", json={"title": "C3", "course_term_id": term_id}, headers=HEADERS).json()["id"]
    # create a person-role
    client.post("/people/", json={"first_name": "T", "last_name": "E", "email": "t@e.com"}, headers=HEADERS)
    pr = client.get("/people/", headers=HEADERS).json()[0]
    prid = pr["roles"][0]["id"]

    assert client.get(f"/courses/{cid}/teachers/", headers=HEADERS).json() == []

    added = client.post(f"/courses/{cid}/teachers/", json={"person_role_id": prid}, headers=HEADERS).json()
    assert added["person_role_id"] == prid

    assert any(t["person_role_id"] == prid for t in client.get(f"/courses/{cid}/teachers/", headers=HEADERS).json())

    r = client.delete(f"/courses/{cid}/teachers/{prid}", headers=HEADERS)
    assert r.status_code == 204
    assert client.get(f"/courses/{cid}/teachers/", headers=HEADERS).json() == []


def test_course_decision_letters_lifecycle():
    # setup course
    client.post("/course-terms/next", headers=HEADERS)
    term_id = client.get("/course-terms/", headers=HEADERS).json()[0]["id"]
    cid = client.post("/courses/", json={"title": "C4", "course_term_id": term_id}, headers=HEADERS).json()["id"]

    assert client.get(f"/courses/{cid}/decision-letters/", headers=HEADERS).json() == []

    added = client.post(
        f"/courses/{cid}/decision-letters/",
        json={"link": "http://x"},
        headers=HEADERS
    ).json()
    dlid = added["id"]
    assert added["link"] == "http://x"

    resp = client.put(f"/courses/{cid}/decision-letters/{dlid}",
                      json={"link": "http://y"},
                      headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json()["link"] == "http://y"

    lst = client.get(f"/courses/{cid}/decision-letters/", headers=HEADERS).json()
    assert any(dl["id"] == dlid for dl in lst)

    r = client.delete(f"/courses/{cid}/decision-letters/{dlid}", headers=HEADERS)
    assert r.status_code == 204
    assert client.get(f"/courses/{cid}/decision-letters/", headers=HEADERS).json() == []

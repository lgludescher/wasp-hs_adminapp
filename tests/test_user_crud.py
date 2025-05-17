from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from app.dependencies import get_db
from app.database import Base
from app.main import app

# Use in-memory SQLite for tests with a single connection pool
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

# Create tables once for the in-memory DB
Base.metadata.create_all(bind=test_engine)


# Override the dependency to use our in-memory DB
def override_get_db():
    # Base.metadata.create_all(bind=test_engine)

    # tables were created once at import; just hand out the session
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Suppress IDE warning about dependency_overrides
app.dependency_overrides[get_db] = override_get_db  # type: ignore
client = TestClient(app)


# this runs before *each* test, giving us a fresh schema every time
@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield


def test_create_and_list_user():
    response = client.post(
        "/users/",
        json={
            "username": "bob",
            "name": "Bob Example",
            "email": "bob@example.com"
        },
        headers={"X-Dev-User": "alice"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "bob"
    assert data["name"] == "Bob Example"
    assert data["email"] == "bob@example.com"
    assert isinstance(data["id"], int)

    response = client.get(
        "/users/",
        headers={"X-Dev-User": "alice"}
    )
    assert response.status_code == 200
    users = response.json()
    usernames = [u["username"] for u in users]
    assert "bob" in usernames


def test_update_user():
    # Create a user “bob”
    client.post(
        "/users/",
        json={"username": "bob", "name": "Bob", "email": "bob@e.com"},
        headers={"X-Dev-User": "alice"}
    )
    # Update “bob” to change name & admin flag
    resp = client.put(
        "/users/bob",
        json={"name": "Bobby", "is_admin": True},
        headers={"X-Dev-User": "alice"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "bob"
    assert data["name"] == "Bobby"
    assert data["is_admin"] is True


def test_delete_user():
    # Create “carol”
    client.post(
        "/users/",
        json={"username": "carol", "name": "Carol", "email": "carol@e.com"},
        headers={"X-Dev-User": "alice"}
    )
    # Delete “carol”
    resp = client.delete(
        "/users/carol",
        headers={"X-Dev-User": "alice"}
    )
    assert resp.status_code == 204
    # Ensure she’s gone
    resp = client.get("/users/", headers={"X-Dev-User": "alice"})
    usernames = [u["username"] for u in resp.json()]
    assert "carol" not in usernames


def test_read_user():
    # create bob
    client.post(
        "/users/",
        json = {"username": "bob", "name": "Bob", "email": "bob@e.com", "is_admin": False},
        headers = {"X-Dev-User": "alice"}
    )

    # admin (alice) can fetch bob
    resp = client.get("/users/bob", headers={"X-Dev-User": "alice"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "bob"

    # non-admin (bob) cannot fetch carol
    client.post(
        "/users/",
        json = {"username": "carol", "name": "Carol", "email": "carol@e.com", "is_admin": False},
        headers = {"X-Dev-User": "alice"}
    )

    resp = client.get("/users/carol", headers={"X-Dev-User": "bob"})
    assert resp.status_code == 403

    # non-admin can fetch their own record
    resp = client.get("/users/bob", headers={"X-Dev-User": "bob"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "bob"


def test_filter_users_by_admin_flag():
    # Seed some users
    client.post(
        "/users/",
        json={"username": "bob", "name": "Bob", "email": "bob@e.com", "is_admin": False},
        headers={"X-Dev-User": "alice"}
    )
    client.post(
        "/users/",
        json={"username": "carol", "name": "Carol", "email": "carol@e.com", "is_admin": True},
        headers={"X-Dev-User": "alice"}
    )

    # Fetch only admins
    resp = client.get("/users?is_admin=true", headers={"X-Dev-User": "alice"})
    assert resp.status_code == 200
    users = resp.json()
    assert all(u["is_admin"] for u in users)
    assert any(u["username"] == "carol" for u in users)

    # Fetch only non-admins
    resp = client.get("/users?is_admin=false", headers={"X-Dev-User": "alice"})
    assert resp.status_code == 200
    users = resp.json()
    assert all(not u["is_admin"] for u in users)
    assert any(u["username"] == "bob" for u in users)


def test_search_users_by_substring():
    # seed two distinct users
    client.post(
        "/users/",
        json={"username": "alpha", "name": "Alice A", "email": "alice@a.com", "is_admin": False},
        headers={"X-Dev-User": "alice"}
    )
    client.post(
        "/users/",
        json={"username": "bravo", "name": "Bob B", "email": "bob@b.com", "is_admin": False},
        headers={"X-Dev-User": "alice"}
    )
    # search matches username
    resp = client.get("/users?search=alp", headers={"X-Dev-User": "alice"})
    assert resp.status_code == 200
    assert [u["username"] for u in resp.json()] == ["alpha"]

    # search matches name
    resp = client.get("/users?search=Bob", headers={"X-Dev-User": "alice"})
    assert resp.status_code == 200
    assert [u["username"] for u in resp.json()] == ["bravo"]

    # search matches email domain
    resp = client.get("/users?search=@b.com", headers={"X-Dev-User": "alice"})
    assert resp.status_code == 200
    assert [u["username"] for u in resp.json()] == ["bravo"]

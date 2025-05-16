from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

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
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Suppress IDE warning about dependency_overrides
app.dependency_overrides[get_db] = override_get_db  # type: ignore
client = TestClient(app)


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

import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker


import worker
from database import Base, JobDB
from main import app, get_db

test_engine = create_engine("sqlite:///test.db")
TestSession = sessionmaker(bind=test_engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    yield
    Base.metadata.drop_all(test_engine)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(worker.time, "sleep", lambda seconds: None)

def test_create_job():
    response= client.post("/jobs", json={"payload": "send email"})
    assert response.status_code == 201
    assert response.json()["status"] == "pending"
    assert response.json()["attempts"] == 0

def test_get_job():
    response = client.post("/jobs", json={"payload": "send email"})
    job_id = response.json()["id"]
    response = client.get(f"/jobs/{job_id}")
    assert response.status_code == 200
    assert response.json()["payload"] == "send email"

def test_get_missing_job_returns_404():
    response = client.get("/jobs/999")
    assert response.status_code == 404

def test_list_jobs_filters_by_status():
    first = client.post("/jobs", json={"payload": "job 1"})
    client.post("/jobs", json={"payload": "job 2"})
    first_id = first.json()["id"]

    db = TestSession()
    job = db.get(JobDB, first_id)
    job.status = "dead"
    db.commit()
    db.close()

    response = client.get("/jobs?status=dead")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == first_id

def test_create_job_without_payload_returns_422():
    response = client.post("/jobs", json={})
    assert response.status_code == 422

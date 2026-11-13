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

def test_once_with_no_jobs_returns_false():
    db = TestSession()
    result = worker.run_once(db)
    assert result is False
    db.close()

def test_successful_job_is_done():
    db = TestSession()
    db.add(JobDB(payload="send email"))
    db.commit()

    result = worker.run_once(db)
    job = db.scalar(select(JobDB).where(JobDB.payload == "send email"))

    assert result is True
    assert job.status == "done"
    assert job.attempts == 1
    db.close()

def test_failed_job_is_retried():
    db = TestSession()
    db.add(JobDB(payload="fail", max_attempts=5))
    db.commit()
    worker.run_once(db)
    job = db.scalar(select(JobDB).where(JobDB.payload == "fail"))
    assert job.status == "pending"
    assert job.attempts == 1
    assert job.last_error == "Simulated processing failure"
    assert job.run_at.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc)
    db.close()

def test_job_dies_after_max_attempts():
    db = TestSession()
    db.add(JobDB(payload="fail", attempts=4))
    db.commit()
    worker.run_once(db)
    job = db.scalar(select(JobDB).where(JobDB.payload == "fail"))
    assert job.status == "dead"
    assert job.attempts == 5
    assert job.last_error == "Simulated processing failure"
    db.close()

def test_job_not_yet_due_is_skipped():
    db = TestSession()
    db.add(JobDB(payload="send email", run_at=datetime.now(timezone.utc) + timedelta(hours=1)))
    db.commit()
    result = worker.run_once(db)
    job = db.scalar(select(JobDB).where(JobDB.payload == "send email"))
    assert result is False
    assert job.status == "pending"
    assert job.attempts == 0
    db.close()

def test_stuck_job_is_recovered():
    db = TestSession()
    long_ago = datetime.now(timezone.utc) - timedelta(minutes=10)
    db.add(JobDB(payload="send email", status="running", attempts=1, locked_at=long_ago))
    db.commit()

    count= worker.recover_stuck_jobs(db)
    job = db.scalar(select(JobDB))

    assert count == 1
    assert job.status == "pending"
    assert job.last_error == "Worker timed out"

def test_stuck_job_out_of_attempts_is_dead():
    db = TestSession()
    long_ago = datetime.now(timezone.utc) - timedelta(minutes=10)
    db.add(JobDB(payload="send email", status="running", attempts=5, locked_at=long_ago))
    db.commit()
    count = worker.recover_stuck_jobs(db)
    job = db.scalar(select(JobDB))
    assert count == 1
    assert job.status == "dead"
    db.close()

def test_recently_claimed_job_is_left_alone():
    db = TestSession()
    just_now = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.add(JobDB(payload="send email", status="running", attempts=1, locked_at=just_now))
    db.commit()
    count = worker.recover_stuck_jobs(db)
    job = db.scalar(select(JobDB))
    assert count == 0
    assert job.status == "running"
    db.close()


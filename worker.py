import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from database import SessionLocal, JobDB

import os


def process(payload:str):
    time.sleep(2)
    if payload == "fail":
        raise Exception("Simulated processing failure")
    print(f"[worker {os.getpid()}] Processed: {payload}")
    return f"Processed: {payload}"

def claim_job(db):
    stmt = (
        select(JobDB)
        .where(JobDB.status == "pending", JobDB.run_at <= datetime.now(timezone.utc))
        .order_by(JobDB.run_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )

    job = db.scalars(stmt).first()
    if job:
        job.status = "running"
        job.attempts += 1
        db.commit()
        db.refresh(job)
    return job

def run_once(db):
    job = claim_job(db)
    if job is None:
        return False
    try:
        process(job.payload)
        job.status = "done"
        job.last_error = None
    except Exception as e:
        handle_failure(job, e)
    db.commit()
    return True

def main():
    while True:
        db = SessionLocal()
        try:
            if not run_once(db):
                time.sleep(1)
        finally:
            db.close()


def handle_failure(job, error):
    job.last_error = str(error)
    if job.attempts >= job.max_attempts:
        job.status = "dead"
    else:
        job.status = "pending"
        job.run_at = datetime.now(timezone.utc) + timedelta(seconds=2 ** job.attempts)


if __name__ == "__main__":
    main()
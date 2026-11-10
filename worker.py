import time
from datetime import datetime, timezone

from sqlalchemy import select

from database import SessionLocal, JobDB


def process(payload:str):
    time.sleep(2)
    if payload == "fail":
        raise Exception("Simulated processing failure")
    print(f"Processed payload: {payload}")
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
        db.commit()
        db.refresh(job)
    return job

def main():
    while True:
        db = SessionLocal()
        try:
            job = claim_job(db)
            if job is None:
                time.sleep(1)
                continue
            process(job.payload)
            job.status="done"
            db.commit()
        finally:
            db.close()

if __name__ == "__main__":
    main()
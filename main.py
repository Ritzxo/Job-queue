from sqlalchemy import select
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import SessionLocal, JobDB



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class JobCreate(BaseModel):
    payload: str


class JobOut(BaseModel):
    id: int
    payload: str
    status: str
    attempts: int
    max_attempts: int
    last_error: str | None

app = FastAPI()

@app.post("/jobs", status_code=201, response_model=JobOut)
def create_job(job: JobCreate, db: Session = Depends(get_db)):
    new_job = JobDB(payload=job.payload)
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    return new_job

@app.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job= db.get(JobDB, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail= f"job '{job_id}' was not found!")
    return job

@app.get("/jobs", response_model=list[JobOut])
def list_jobs(status: str | None = None, db: Session = Depends(get_db)):
    stmt = select(JobDB)
    if status is not None:
        stmt = stmt.where(JobDB.status == status)
    stmt = stmt.order_by(JobDB.id)
    jobs = db.scalars(stmt).all()
    return jobs

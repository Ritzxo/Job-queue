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
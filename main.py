from datetime import datetime

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
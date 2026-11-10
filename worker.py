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


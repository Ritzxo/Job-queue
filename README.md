# job-queue

A small background job queue built with Python, FastAPI and PostgreSQL.

Clients add jobs through an HTTP API. The API only records the job and replies straight
away. A separate worker process picks jobs up and runs them. If a job fails, the worker
retries it with increasing delays, and after too many failures the job is parked as
"dead" so a person can inspect it.

I'm building it to learn the reliability ideas behind real event-processing systems:
retries, backoff, dead-letter queues, and safe concurrency between workers. It is the
second project in my portfolio, after [inventory-api](https://github.com/Ritzxo/inventory-api).

**Status: in progress.** See the roadmap below for what works today.

## How it works

```
client --> API (POST /jobs) --> [ jobs table in Postgres ] <-- worker (separate process)
                                                                 claims a job, runs it,
                                                                 retries or marks it dead
```

- **The API** accepts a job, stores it with status `pending`, and returns its id.
- **The worker** repeatedly claims a job that is due, runs it, and records the result.
- **Retries** use exponential backoff: wait 1s, then 2s, then 4s, and so on, so a failing
  service gets time to recover.
- **Dead-letter state:** after `max_attempts` failures a job becomes `dead` instead of
  retrying forever.

The reasoning behind these choices is in [DESIGN.md](DESIGN.md).

## Run it locally

Requires Python 3.12+ and Docker Desktop.

```bash
python -m venv .venv
# Windows (PowerShell):
.venv\Scripts\activate
# macOS / Linux:
# source .venv/bin/activate

pip install -r requirements.txt

# start Postgres (listens on port 5433 on your machine)
docker compose up -d

# create the jobs table
python database.py

# start the API
uvicorn main:app --reload
```

Then open <http://127.0.0.1:8000/docs> for the interactive API documentation.

## Roadmap

- [x] Project setup, virtual environment, `.gitignore`
- [x] Postgres in Docker Compose
- [x] `jobs` table (SQLAlchemy model)
- [x] Request and response models, database session dependency
- [x] `POST /jobs` to add a job
- [x] `GET /jobs/{id}` to check a job
- [x] Worker that claims and runs pending jobs
- [x] Retries with exponential backoff
- [x] Dead-letter state after `max_attempts` failures
- [x] Safe with several workers at once (`FOR UPDATE SKIP LOCKED`)
- [x] `GET /jobs?status=dead` to list failed jobs
- [ ] Automated tests with pytest, run in GitHub Actions

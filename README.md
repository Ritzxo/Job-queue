# job-queue

[![Tests](https://github.com/Ritzxo/job-queue/actions/workflows/tests.yml/badge.svg)](https://github.com/Ritzxo/job-queue/actions/workflows/tests.yml)

A small background job queue built with Python, FastAPI and PostgreSQL.

Clients add jobs through an HTTP API. The API only records the job and replies straight
away. A separate worker process picks jobs up and runs them. If a job fails, the worker
retries it with increasing delays, and after too many failures the job is parked as
"dead" so a person can inspect it.

I'm building it to learn the reliability ideas behind real event-processing systems:
retries, backoff, dead-letter queues, and safe concurrency between workers. It is the
second project in my portfolio, after [inventory-api](https://github.com/Ritzxo/inventory-api).

**Status: complete.** Everything on the roadmap below is built and tested.

## How it works

```
client --> API (POST /jobs) --> [ jobs table in Postgres ] <-- worker (separate process)
                                                                 claims a job, runs it,
                                                                 retries or marks it dead
```

- **The API** accepts a job, stores it with status `pending`, and returns its id.
- **The worker** repeatedly claims a job that is due, runs it, and records the result.
- **Retries** use exponential backoff: the wait is `2 ** attempts` seconds, so 2s after
  the first failure, then 4s, 8s and 16s, giving a failing service time to recover.
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

# create your local settings file, then edit .env and set your own password
# Windows (PowerShell):
Copy-Item .env.example .env
# macOS / Linux:
# cp .env.example .env

# start Postgres (listens on port 5433 on your machine)
docker compose up -d

# create the jobs table
python database.py

# start the API
uvicorn main:app --reload
```

Then open <http://127.0.0.1:8000/docs> for the interactive API documentation.

In a second terminal, start the worker:

```bash
python worker.py
```

## Run the tests

```bash
pytest -v
```

The tests cover every API endpoint and the worker's job lifecycle: a successful job is
marked done, a failed job is retried with its next run pushed into the future, a job that
reaches `max_attempts` becomes dead, a job that isn't due yet is skipped, and jobs stuck in
`running` after a crash are recovered. They use a throwaway SQLite database, so Postgres
doesn't need to be running, and they run automatically on every push through GitHub Actions.

Because the tests use SQLite, they can't check the `FOR UPDATE SKIP LOCKED` row locking
(SQLite doesn't support it). That was checked by hand instead, by running two workers
against Postgres and confirming every job ran exactly once.

## Configuration

Settings are read from environment variables, loaded from a `.env` file if there is one.
`.env` is ignored by git, so passwords stay out of the repository; `.env.example` shows
what to set.

| Variable | Used by | Purpose |
|---|---|---|
| `DATABASE_URL` | `database.py` | How the API and worker connect to Postgres |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | `docker-compose.yml` | Create the Postgres user and database |

Tables are created by running `python database.py` once, not every time the code is
imported.

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
- [x] Automated tests with pytest, run in GitHub Actions
- [x] Crash recovery: jobs stuck in `running` after a worker dies are retried or marked dead

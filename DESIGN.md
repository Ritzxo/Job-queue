# Design

This document explains how the job queue is designed and why. It will grow as the
project does.

## Goals

- Accept work quickly and do it in the background, so callers never wait on slow tasks.
- Survive failures: temporary errors are retried, permanent ones are kept for inspection.
- Never lose a job, and never let two workers run the same job at the same time.

## The `jobs` table

| Column | Type | Purpose |
|---|---|---|
| `id` | integer, primary key | Assigned by Postgres |
| `payload` | text, required | The data describing the work to do |
| `status` | text, required | `pending`, `running`, `done` or `dead` |
| `attempts` | integer, required | How many times the job has been tried |
| `max_attempts` | integer, required | Attempts allowed before the job becomes `dead` |
| `run_at` | timestamp with time zone, required | The earliest time the job may run |
| `last_error` | text, optional | The most recent failure message, empty until a job fails |

The default values (`pending`, 0 attempts, 5 max attempts, `run_at` set to now) are
applied by the application when it creates a job, not stored in the database. A row
inserted by hand has to supply them itself.

## Job lifecycle

```
pending --> running --> done
   ^           |
   |           v  (failure, attempts < max_attempts)
   +--- pending again, run_at pushed into the future (backoff)
               |
               v  (failure, attempts == max_attempts)
             dead
```

## Planned design decisions

- **A table in Postgres is the queue.** It keeps the system simple (one fewer service),
  and jobs are stored durably. A dedicated broker such as Kafka may replace it in the
  final-year project, which is why the API and worker are kept separate.
- **Exponential backoff for retries.** Failures are often temporary. Retrying
  immediately hammers a service that is already struggling, so each retry waits longer
  than the last. Random jitter will be added so many failed jobs don't all retry at the
  same moment.
- **Dead-letter state.** Some jobs never succeed. Capping attempts stops them looping
  forever and keeps them visible for a person to look at.
- **`FOR UPDATE SKIP LOCKED` for claiming jobs.** With several workers, two could read
  the same pending job and both run it. Locking the row while claiming it, and letting
  other workers skip locked rows, prevents that.
- **The API never runs jobs.** `POST /jobs` only records work and returns the id. This
  keeps responses fast and lets the worker be scaled or restarted independently.

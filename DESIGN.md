# Design

This document explains how the job queue is designed and why. It will grow as the
project does.

## Goals

- Accept work quickly and do it in the background, so callers never wait on slow tasks.
- Survive failures: temporary errors are retried, permanent ones are kept for inspection.
- Never lose a job, and make sure every job runs at least once (see the at-least-once
  trade-off below).

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
| `locked_at` | timestamp with time zone, optional | When a worker last claimed the job |

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

## Design decisions

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
- **Recovering jobs after a worker crash.** A worker sets a job to `running` and commits
  before doing the work. If the worker then dies, nothing would ever change that status,
  and other workers only look for `pending` jobs, so the job would be stuck forever. Each
  claim records `locked_at`, and every worker loop first looks for jobs that have been
  `running` for longer than a timeout (5 minutes). Those count as a failed attempt: they go
  back to `pending` if they have attempts left, or to `dead` if not. The attempt was already
  counted when the job was claimed, so a job that keeps crashing workers still reaches its
  limit.
- **At-least-once, not exactly-once.** Recovery can't tell a dead worker from a slow one.
  If a worker is still alive but takes longer than the timeout, another worker can reclaim
  the job and both may finish it, so a job can occasionally run twice. That's the price of
  never losing a job. Jobs should therefore be idempotent, meaning safe to run twice (for
  example, record "email sent for job 42" and check it first). Ways to narrow the window:
  a longer timeout than any job should take, a worker heartbeat that keeps refreshing
  `locked_at` while it works, and having a worker only mark a job done if it still owns it.
- **The API never runs jobs.** `POST /jobs` only records work and returns the id. This
  keeps responses fast and lets the worker be scaled or restarted independently.

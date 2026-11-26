# Performance tuning log (NF-01)

NF-01: p95 API response time < 2 s with 50 concurrent users. Test: `tests/perf/load_test.py`,
50 users × 10 queries each, no think time (worst case), against the Docker deployment on the
development PC (Docker Desktop, 28 logical CPUs, 16 GB RAM). The final run is reported in
[`performance.md`](performance.md); the earlier runs below were recorded from the same script.

| Run | Configuration | Mean | p95 | Throughput | NF-01 |
|---|---|---|---|---|---|
| 1 | 2 gunicorn workers × 4 threads; library defaults (PyTorch ≈ 20 threads, OpenBLAS/tokenizers one thread per core) | 2429 ms | 3743 ms | 18.8 req/s | **Fail** |
| 2 | 6 workers × 4 threads; `torch.set_num_threads(2)`; settings read in one query; suggestion FAQs fetched in one query | 1341 ms | 2831 ms | 32.8 req/s | **Fail** |
| 3 | Run 2 + `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `TOKENIZERS_PARALLELISM=false` | 419 ms | 802 ms | 106.3 req/s | **Pass** |
| 4 | Run 3 configuration, **60-second** run instead of 10 queries per user (6,167 requests) | 490 ms | 2006 ms | 101.0 req/s | **Fail** |
| 4b | Run 3 configuration, 60 s, FAQ edited at 30 s (LT-3 before the fix) | 565 ms | 1717 ms | 87.6 req/s | Pass (whole run) |
| 5 | Run 3 + `--worker-connections 4` (trial through `GUNICORN_CMD_ARGS`), 60 s | 441 ms | 534 ms | 113.1 req/s | **Pass** |
| 6 (final LT-2) | `--worker-connections 4` baked into `backend/Dockerfile`, 60 s | 442 ms | 535 ms | 112.8 req/s | **Pass** |
| 7 (final LT-3) | Run 6 configuration, 60 s, FAQ edited at 30 s | 499 ms | 529 ms | 99.9 req/s | Pass (whole run) |

Reports of runs 3–5 are kept in [`lt_runs/`](lt_runs/); run 6 is [`performance.md`](performance.md) and run 7 is
[`performance_rebuild.md`](performance_rebuild.md).

## What was wrong
During run 2 the API container used ~2 780 % CPU (all 28 cores) while serving only ~33
requests per second — far more CPU than the small MiniLM model needs. Each of the 6 worker
processes started its own BLAS/OpenMP and tokenizer thread pools sized to the number of cores,
so ~170 busy-waiting threads competed for 28 cores. Pinning those libraries to one thread per
worker (process-level parallelism comes from gunicorn instead) removed the contention and
tripled throughput.

## Second problem: uneven load across workers (runs 4–6)
Run 3 lasted only 4.7 s (500 requests). Over 60 s the same configuration reached p95 2006 ms (run 4) with a
very skewed distribution (median 256 ms). With gunicorn's threaded workers each worker keeps accepting
connections while all of its threads are busy, so some requests queued behind a busy worker while other
workers were free. Setting `--worker-connections` equal to the number of threads (4) makes a busy worker stop
accepting, so waiting requests stay in the shared socket backlog and go to the next free worker. p95 fell to
535 ms with higher throughput (run 6).

## Index rebuild under load (runs 4b and 7)
A single rebuild of the 210-FAQ index takes 2636 ms on average (10 runs, SD 55 ms; `rebuild_timing.json`,
measured inside the API container). Under full load all six workers rebuild at the same moment and compete for
the CPU, so for about 8 s after the edit every in-flight request waits: 56 requests were delayed, the slowest
by 8258 ms (run 7). The whole-run p95 stays at 529 ms, so NF-01 as defined (p95 over the run) is met, but
individual requests just after an FAQ change exceed two seconds. A background rebuild that keeps serving the
old index until the new one is ready would remove this stall (future work).

## Settings now used (configurable in `docker-compose.yml` / `.env`)
`GUNICORN_WORKERS=6`, `GUNICORN_THREADS=4` (and `--worker-connections` = threads), `TORCH_THREADS=2`, and the single-thread BLAS/OpenMP
environment variables baked into `backend/Dockerfile`. Memory use of the API container is about
4 GB with 6 workers (each loads its own copy of the SBERT model); on a smaller server use fewer
workers, e.g. `GUNICORN_WORKERS=2` for a 4 GB machine (Table 13 minimum), and re-run the load test.

Note: the per-IP chat rate limit was raised for these runs (`CHAT_RATE_LIMIT="100000 per minute"`)
because all 50 simulated users share one IP address.

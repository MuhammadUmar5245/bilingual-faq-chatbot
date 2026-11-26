"""Performance test for NF-01: p95 response time < 2 s with 50 concurrent users.

50 simulated users (threads) start together; each sends 10 chat queries drawn from the test
query set back-to-back with no think time (a worst case - real students pause between messages).
All requests come from one machine/IP, so the API's per-IP chat rate limit must be raised for
the run, e.g.:  CHAT_RATE_LIMIT="100000 per minute" docker compose up -d api

Usage (from backend/):  python -m tests.perf.load_test --base http://localhost:8088
Outputs: docs/results/performance.md, performance_requests.csv, performance.png

LT-3, test during an FAQ index rebuild (Section 4.2): run for a fixed duration and edit one FAQ
through the admin API in the middle of the run, so every gunicorn worker rebuilds its index:
    python -m tests.perf.load_test --duration 60 --edit-at 30 --tag rebuild
Outputs: docs/results/performance_rebuild.md, performance_rebuild_requests.csv, performance_rebuild.png
"""
import argparse
import csv
import random
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import numpy as np
import requests

PROJECT = Path(__file__).resolve().parents[3]
OUT = PROJECT / "docs" / "results"
TARGET_MS = 2000


ADMIN = ("admin", "Admin@12345")
EDIT_FAQ_ID = 1


def edit_faq(base, marker):
    """Change one FAQ's keywords via the admin API; this bumps faq_version, so each worker rebuilds."""
    s = requests.Session()
    s.post(f"{base}/api/admin/login", json={"username": ADMIN[0], "password": ADMIN[1]}, timeout=30).raise_for_status()
    faq = s.get(f"{base}/api/admin/faqs/{EDIT_FAQ_ID}", timeout=30).json()
    kw = faq["keywords"].replace(", loadtest-edit", "")
    if marker:
        kw += ", loadtest-edit"
    s.put(f"{base}/api/admin/faqs/{EDIT_FAQ_ID}", json={"keywords": kw}, timeout=60).raise_for_status()


def run(base, users, per_user, seed=42, duration=None, edit_at=None):
    queries = [r["query"] for r in csv.DictReader(open(PROJECT / "data" / "test_queries.csv", encoding="utf-8"))]
    rng = random.Random(seed)
    plan = [[rng.choice(queries) for _ in range(per_user)] for _ in range(users)]
    t_start = [0.0]
    results = []
    lock = threading.Lock()

    edit = {}

    def user(uid):
        s = requests.Session()
        u_rng = random.Random(seed + uid)
        barrier.wait()
        if uid == 0:
            t_start[0] = time.perf_counter()
        deadline = time.perf_counter() + duration if duration else None
        i = 0
        while (i < per_user) if deadline is None else (time.perf_counter() < deadline):
            q = plan[uid][i] if deadline is None else u_rng.choice(queries)
            i += 1
            t0 = time.perf_counter()
            try:
                r = s.post(f"{base}/api/chat", json={"message": q, "session_id": f"load-{uid}"}, timeout=60)
                status = r.status_code
                method = r.json().get("method") if r.ok else ""
            except requests.RequestException as e:
                status, method = f"error:{type(e).__name__}", ""
            t1 = time.perf_counter()
            with lock:
                results.append({"user": uid, "start_s": t0, "ms": (t1 - t0) * 1000, "status": status, "method": method})

    def editor():
        barrier.wait()
        time.sleep(edit_at)
        edit["t"] = time.perf_counter()
        edit_faq(base, marker=True)
        edit["done"] = time.perf_counter()

    n_threads = users + (1 if edit_at is not None else 0)
    barrier = threading.Barrier(n_threads)
    with ThreadPoolExecutor(max_workers=n_threads) as pool:
        futures = [pool.submit(user, u) for u in range(users)]
        if edit_at is not None:
            futures.append(pool.submit(editor))
        for f in futures:
            f.result()
    if edit_at is not None:
        edit_faq(base, marker=False)  # restore the FAQ after the run
    t0 = min(r["start_s"] for r in results)
    for r in results:
        r["start_s"] = round(r["start_s"] - t0, 3)
        r["ms"] = round(r["ms"], 1)
    if edit:
        edit = {"edit_s": round(edit["t"] - t0, 3), "edit_api_ms": round((edit["done"] - edit["t"]) * 1000, 1)}
    return results, edit


def window_stats(results, edit, window_s):
    """LT-3: compare requests before the FAQ edit with requests that started in the rebuild window."""
    ok = [r for r in results if r["status"] == 200]
    e = edit["edit_s"]
    before = np.array([r["ms"] for r in ok if r["start_s"] + r["ms"] / 1000 < e])
    win = np.array([r["ms"] for r in ok if e <= r["start_s"] < e + window_s])
    # A request "pays" for the rebuild if it overlaps the edit and is slower than anything seen before it
    straddle = [r for r in ok if r["start_s"] < e + window_s and r["start_s"] + r["ms"] / 1000 > e]
    delayed = [r for r in straddle if r["ms"] > before.max()]
    return {"edit_s": e, "edit_api_ms": edit["edit_api_ms"], "window_s": window_s,
            "before_n": len(before), "before_p95": float(np.percentile(before, 95)), "before_p99": float(np.percentile(before, 99)),
            "before_max": float(before.max()), "window_n": len(win), "window_p95": float(np.percentile(win, 95)),
            "window_max": float(win.max()), "delayed": len(delayed),
            "delayed_max": max((r["ms"] for r in delayed), default=0.0)}


def report(results, base, users, per_user, tag="", edit=None, window_s=10.0, duration=None):
    suffix = f"_{tag}" if tag else ""
    ok = [r for r in results if r["status"] == 200]
    ms = np.array([r["ms"] for r in ok])
    duration = max(r["start_s"] + r["ms"] / 1000 for r in results)
    stats = {
        "requests": len(results), "successful": len(ok), "errors": len(results) - len(ok),
        "mean": ms.mean(), "median": np.median(ms), "p90": np.percentile(ms, 90), "p95": np.percentile(ms, 95),
        "p99": np.percentile(ms, 99), "max": ms.max(), "min": ms.min(), "throughput": len(ok) / duration,
        "duration": duration,
    }
    passed = stats["p95"] < TARGET_MS and stats["errors"] == 0
    with open(OUT / f"performance{suffix}_requests.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0]))
        w.writeheader()
        w.writerows(sorted(results, key=lambda r: r["start_s"]))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.grid": True, "grid.color": "#e6e5e0"})
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
    ax = axes[0]
    ax.hist(ms, bins=40, color="#2a78d6", edgecolor="white", linewidth=1)
    ax.axvline(stats["p95"], color="#eb6834", lw=2, ls="--")
    ax.text(stats["p95"], ax.get_ylim()[1] * 0.92, f"  p95 = {stats['p95']:.0f} ms", color="#2b2b2a", fontsize=9)
    ax.set_xlabel("Response time (ms)")
    ax.set_ylabel("Requests")
    ax.set_title(f"A. Response-time distribution ({users} concurrent users)", loc="left")
    ax = axes[1]
    xs = [r["start_s"] for r in ok]
    ax.scatter(xs, [r["ms"] for r in ok], s=10, color="#2a78d6", alpha=0.6, edgecolors="none", label="request")
    ax.axhline(TARGET_MS, color="#eb6834", lw=1.5, ls="--")
    ax.text(0, TARGET_MS * 1.02, "NF-01 target: 2000 ms", color="#52514e", fontsize=8)
    ax.axhline(stats["p95"], color="#1baf7a", lw=1.5)
    ax.text(0, stats["p95"] * 1.04, f"p95 {stats['p95']:.0f} ms", color="#52514e", fontsize=8)
    ax.set_ylim(0, max(TARGET_MS * 1.15, ms.max() * 1.05))
    ax.set_xlabel("Time since test start (s)")
    ax.set_ylabel("Response time (ms)")
    if edit:
        ax.axvspan(edit["edit_s"], edit["edit_s"] + window_s, color="#f1f0ec", zorder=0)
        ax.axvline(edit["edit_s"], color="#52514e", lw=1)
        ax.text(edit["edit_s"], TARGET_MS * 0.85, "  FAQ edited\n  (index rebuild)", color="#52514e", fontsize=8)
    ax.set_title("B. Response time during the test", loc="left")
    fig.tight_layout()
    fig.savefig(OUT / f"performance{suffix}.png", dpi=160)
    plt.close(fig)

    methods = {m: sum(r["method"] == m for r in ok) for m in ("tfidf", "sbert", "fallback")}
    codes = {}
    for r in results:
        codes[str(r["status"])] = codes.get(str(r["status"]), 0) + 1
    load = (f"for {duration:.0f} s, each user sending its next query as soon as the answer arrives"
            if duration else f"{per_user} queries each")
    md = [
        "# Performance test (NF-01)" + (" — LT-3, during an FAQ index rebuild" if edit else ""), "",
        "Generated by `python -m tests.perf.load_test` — do not edit by hand.", "",
        f"- Target: {base}  ·  run {datetime.now():%Y-%m-%d %H:%M}",
        f"- Load: **{users} concurrent users**, {load}, no think time ({len(results)} requests; "
        "all users start together, no ramp-up)",
        f"- HTTP status codes: {codes}; error rate {stats['errors'] / stats['requests'] * 100:.2f} %",
        "- Queries drawn at random from `data/test_queries.csv` (English and Arabic, incl. out-of-scope)",
        f"- Answer methods: {methods}", "",
        "| Metric | Value |", "|---|---|",
        f"| Successful requests | {stats['successful']} / {stats['requests']} (errors: {stats['errors']}) |",
        f"| Mean | {stats['mean']:.0f} ms |",
        f"| Median (p50) | {stats['median']:.0f} ms |",
        f"| p90 | {stats['p90']:.0f} ms |",
        f"| **p95** | **{stats['p95']:.0f} ms** |",
        f"| p99 | {stats['p99']:.0f} ms |",
        f"| Min / max | {stats['min']:.0f} / {stats['max']:.0f} ms |",
        f"| Throughput | {stats['throughput']:.1f} requests/s over {stats['duration']:.1f} s |", "",
        f"**NF-01 (p95 < 2000 ms with 50 concurrent users): {'PASS' if passed else 'FAIL'}**", "",
        "Note: the per-IP chat rate limit was raised for this run because all simulated users share one IP address.",
        "", f"![Performance](performance{suffix}.png)",
    ]
    if edit:
        w = window_stats(results, edit, window_s)
        md[-1:-1] = [
            "## Index rebuild window", "",
            f"FAQ #{EDIT_FAQ_ID} was edited through the admin API at t = {w['edit_s']:.1f} s (the admin request took "
            f"{w['edit_api_ms']:.0f} ms). Every worker rebuilds its index on its next chat request.", "",
            "| Measure | Value |", "|---|---|",
            f"| Before the edit: requests / p95 / p99 / max | {w['before_n']} / {w['before_p95']:.0f} / "
            f"{w['before_p99']:.0f} / {w['before_max']:.0f} ms |",
            f"| Rebuild window ({window_s:.0f} s after the edit): requests started | {w['window_n']} |",
            f"| Rebuild window: p95 / max | {w['window_p95']:.0f} / {w['window_max']:.0f} ms |",
            f"| Delayed requests (overlapping the edit and slower than any request before it) | {w['delayed']} "
            f"(slowest {w['delayed_max']:.0f} ms) |",
            f"| **Whole run p95** | **{stats['p95']:.0f} ms** |", "",
            f"**NF-01 during a rebuild (whole-run p95 < 2000 ms, no errors): {'PASS' if passed else 'FAIL'}**", "",
        ]
        import json
        (OUT / f"performance{suffix}.json").write_text(
            json.dumps({"stats": stats, "window": w, "status_codes": codes}, indent=2, default=float), encoding="utf-8")
    (OUT / f"performance{suffix}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md[:20]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8088")
    ap.add_argument("--users", type=int, default=50)
    ap.add_argument("--per-user", type=int, default=10)
    ap.add_argument("--duration", type=float, default=None, help="run for N seconds instead of --per-user queries")
    ap.add_argument("--edit-at", type=float, default=None, help="LT-3: edit an FAQ N seconds into the run")
    ap.add_argument("--window", type=float, default=10.0, help="LT-3: rebuild window length in seconds")
    ap.add_argument("--tag", default="", help="suffix for the output files, e.g. 'rebuild'")
    a = ap.parse_args()
    base = a.base.rstrip("/")
    for _ in range(20):  # warm up every worker
        requests.post(f"{base}/api/chat", json={"message": "warm up"}, timeout=60)
    results, edit = run(base, a.users, a.per_user, duration=a.duration, edit_at=a.edit_at)
    report(results, base, a.users, a.per_user, tag=a.tag, edit=edit or None, window_s=a.window, duration=a.duration)


if __name__ == "__main__":
    main()

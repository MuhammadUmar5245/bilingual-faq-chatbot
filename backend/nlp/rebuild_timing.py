"""Measure the FAQ index rebuild time (Section 4.2, effect on NF-01).

After staff change an FAQ, the first chat request each worker receives rebuilds that worker's
index: TF-IDF, the category classifier and the sentence-BERT embeddings. The FAQ texts have
changed, so the embedding cache misses and every FAQ is re-encoded; this script reproduces that
case (cache disabled). The model itself is loaded once per worker and is not part of a rebuild.

Usage (from backend/, ideally inside the API container so the deployed thread limits apply):
    python -m nlp.rebuild_timing --runs 10 --out rebuild_timing.json
"""
import argparse
import json
import os
import platform
import statistics
import time

from nlp.evaluate import load_faqs
from nlp.hybrid import HybridRetriever
from nlp.sbert_retriever import load_model


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    faqs = load_faqs()
    load_model("paraphrase-multilingual-MiniLM-L12-v2")  # loaded once per worker, not per rebuild
    HybridRetriever(sbert_cache=False).fit(faqs)  # warm-up run, not counted
    times = []
    for _ in range(a.runs):
        t0 = time.perf_counter()
        HybridRetriever(sbert_cache=False).fit(faqs)
        times.append((time.perf_counter() - t0) * 1000)
    res = {
        "faqs": len(faqs), "runs": a.runs, "mean_ms": statistics.mean(times), "sd_ms": statistics.stdev(times),
        "min_ms": min(times), "max_ms": max(times), "times_ms": [round(t, 1) for t in times],
        "env": {"python": platform.python_version(), "machine": platform.machine(),
                "cpu_count": os.cpu_count(), "torch_threads": os.getenv("TORCH_THREADS", "2"),
                "omp_num_threads": os.getenv("OMP_NUM_THREADS")},
    }
    print(json.dumps(res, indent=2))
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2)


if __name__ == "__main__":
    main()

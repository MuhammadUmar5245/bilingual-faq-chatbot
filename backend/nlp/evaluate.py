"""Quasi-experiment (Chapter 3.2.1): keyword match vs TF-IDF vs SBERT vs Hybrid (NF-02).

Usage (from backend/):  python -m nlp.evaluate

Protocol
  * Knowledge base: data/faqs_seed.csv (FAQ id = row number).
  * Test set: data/test_queries.csv (361 queries, 32 out-of-scope labelled NONE).
  * The test set is split by query_id: odd ids = TUNING split (used only to choose each
    method's thresholds), even ids = HELD-OUT split (never used for any decision).
    Results are reported on the held-out split and on the full set.
  * A prediction is correct when the returned FAQ id equals the expected id, or when the
    system returns the fallback for an out-of-scope (NONE) query.

Outputs go to docs/results/. Nothing in this file contains result numbers - every figure
is computed from actually running the retrievers.
"""
import csv
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from nlp.hybrid import HybridRetriever  # noqa: E402
from nlp.classifier import CategoryClassifier  # noqa: E402
from nlp.language import detect_language  # noqa: E402
from nlp.preprocess import AR_STOP, EN_STOP, normalize_text  # noqa: E402
from nlp.sbert_retriever import SbertRetriever  # noqa: E402
from nlp.tfidf_retriever import FaqDoc, TfidfRetriever  # noqa: E402

PROJECT = BACKEND.parent
DATA = PROJECT / "data"
OUT = PROJECT / "docs" / "results"

CATEGORIES = ["Admissions", "Registration", "Fees", "Academic Programmes", "Examinations", "Student Services"]
SPEC_TFIDF_THRESHOLD = 0.75  # value from Chapter 3.6, kept for the TF-IDF stage of the hybrid
GRID = np.round(np.arange(0.05, 0.96, 0.01), 2)
FUSION_GRID = [0.3, 0.4, 0.5, 0.6, 0.7]


# --------------------------------------------------------------------------- data
def load_faqs() -> list[FaqDoc]:
    with open(DATA / "faqs_seed.csv", encoding="utf-8") as f:
        return [FaqDoc(i, r["question_en"], r.get("question_ar", ""), r.get("keywords", ""), r["category"],
                       r["answer"], r.get("answer_ar", ""))
                for i, r in enumerate(csv.DictReader(f), start=1)]


def load_queries() -> list[dict]:
    with open(DATA / "test_queries.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# --------------------------------------------------------------------------- baseline
class KeywordRetriever:
    """Baseline: fraction of the query's content words found in the FAQ question/keywords.
    No stemming, no synonyms, no weighting - represents a static FAQ page keyword search."""

    @staticmethod
    def _words(text):
        return {t for t in normalize_text(text).split() if t not in EN_STOP and t not in AR_STOP}

    def fit(self, faqs):
        self.docs = [(self._words(f"{f.question_en} {f.keywords}"), self._words(f.question_ar)) for f in faqs]
        return self

    def scores(self, query):
        q = self._words(query)
        if not q:
            return np.zeros(len(self.docs))
        return np.array([max(len(q & en), len(q & ar)) / len(q) for en, ar in self.docs])


# --------------------------------------------------------------------------- decisions
def decide_single(M, th):
    best = M.max(axis=1)
    return np.where(best >= th, M.argmax(axis=1) + 1, 0)


def decide_hybrid(T, S, tfidf_th, w, sbert_th):
    stage1 = T.max(axis=1) >= tfidf_th
    F = w * T + (1 - w) * S
    pred_f = np.where(F.max(axis=1) >= sbert_th, F.argmax(axis=1) + 1, 0)
    pred = np.where(stage1, T.argmax(axis=1) + 1, pred_f)
    method = np.where(stage1, "tfidf", np.where(pred_f > 0, "sbert", "fallback"))
    return pred, method


# --------------------------------------------------------------------------- metrics
def metrics(y, pred, mask, cat_of):
    from sklearn.metrics import precision_recall_fscore_support
    y, pred = y[mask], pred[mask]
    ins = y > 0
    yt = [str(v) if v else "NONE" for v in y]
    yp = [str(v) if v else "NONE" for v in pred]
    p, r, f1, _ = precision_recall_fscore_support(yt, yp, average="macro", zero_division=0)
    pw, rw, f1w, _ = precision_recall_fscore_support(yt, yp, average="weighted", zero_division=0)
    cat_true = np.array([cat_of.get(v, "NONE") for v in y])
    cat_pred = np.array([cat_of.get(v, "NONE") for v in pred])
    return {
        "n": int(len(y)),
        "accuracy": float((y == pred).mean()),
        "in_scope_accuracy": float((y[ins] == pred[ins]).mean()) if ins.any() else float("nan"),
        "oos_rejection": float((pred[~ins] == 0).mean()) if (~ins).any() else float("nan"),
        "fallback_rate": float((pred == 0).mean()),
        "precision_macro": float(p), "recall_macro": float(r), "f1_macro": float(f1),
        "precision_weighted": float(pw), "recall_weighted": float(rw), "f1_weighted": float(f1w),
        "category_accuracy": float((cat_true == cat_pred).mean()),
    }


def tune_single(M, y, dev, cat_of):
    accs = [metrics(y, decide_single(M, th), dev, cat_of)["accuracy"] for th in GRID]
    return float(GRID[int(np.argmax(accs))])


def tune_hybrid(T, S, y, dev, cat_of, weights):
    best = (-1, None, None)
    for w in weights:
        for th in GRID:
            acc = metrics(y, decide_hybrid(T, S, SPEC_TFIDF_THRESHOLD, w, th)[0], dev, cat_of)["accuracy"]
            if acc > best[0] + 1e-12:
                best = (acc, w, float(th))
    return best[1], best[2]


# --------------------------------------------------------------------------- extra analyses
def svm_report(pred, true, mask, lang):
    """NF-02: linear SVM intent (category) accuracy on the in-scope held-out queries (Table 25).
    The SVM is trained on FAQ questions and keywords only, never on test queries."""
    from sklearn.metrics import precision_recall_fscore_support
    p, t, lg = pred[mask], true[mask], lang[mask]
    prec, rec, f1, sup = precision_recall_fscore_support(t, p, labels=CATEGORIES, zero_division=0)
    per_cat = [{"category": c, "n": int(sup[i]), "correct": int(((t == c) & (p == c)).sum()),
                "precision": float(prec[i]), "recall": float(rec[i]), "f1": float(f1[i])}
               for i, c in enumerate(CATEGORIES)]
    per_lang = {g: {"n": int((lg == g).sum()), "correct": int(((lg == g) & (p == t)).sum())} for g in ("en", "ar")}
    plot_svm_confusion(t, p)
    return {"n": int(mask.sum()), "correct": int((p == t).sum()), "accuracy": float((p == t).mean()),
            "per_category": per_cat, "per_language": per_lang}


def sensitivity_table(T, S, y, dev, cat_of, sbert_th, w):
    """Tuning-split accuracy at the chosen values and their neighbours (Table 16).
    One parameter is varied at a time; the other two keep their chosen values."""
    def row(param, value, tt, ww, th):
        m = metrics(y, decide_hybrid(T, S, tt, ww, th)[0], dev, cat_of)
        return {"parameter": param, "value": value, "accuracy": m["accuracy"], "oos_rejection": m["oos_rejection"],
                "fallback_rate": m["fallback_rate"]}
    rows = [row("tfidf_threshold", v, v, w, sbert_th) for v in (0.65, 0.70, 0.75, 0.80, 0.85)]
    rows += [row("fused_threshold", v, SPEC_TFIDF_THRESHOLD, w, v) for v in (0.25, 0.30, 0.35, 0.40, 0.45)]
    rows += [row("tfidf_weight", v, SPEC_TFIDF_THRESHOLD, v, sbert_th) for v in (0.4, 0.5, 0.6, 0.7, 0.8)]
    write_csv(OUT / "tuning_sensitivity.csv", [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}
                                               for r in rows])
    return rows


def margin_table(T, S, y, dev, test, w, sbert_th):
    """Near-miss analysis (TC40-TC43): effect of a clarification margin rule that refuses a fused-stage
    answer when best - second-best fused score < m. Reported, not adopted (Section 5.2.2)."""
    st1 = T.max(axis=1) >= SPEC_TFIDF_THRESHOLD
    F = w * T + (1 - w) * S
    srt = np.sort(F, axis=1)
    rows = []
    for m in (0.0, 0.02, 0.04, 0.06, 0.08, 0.10):
        ok = (srt[:, -1] >= sbert_th) & (srt[:, -1] - srt[:, -2] >= m)
        pred = np.where(st1, T.argmax(axis=1) + 1, np.where(ok, F.argmax(axis=1) + 1, 0))
        r = {"margin": m}
        for name, mask in (("tuning", dev), ("held_out", test)):
            yy, pp = y[mask], pred[mask]
            r[f"{name}_accuracy"] = float((yy == pp).mean())
            r[f"{name}_wrong_answer_rate"] = float(((yy != pp) & (pp > 0)).mean())
            r[f"{name}_fallback_rate"] = float((pp == 0).mean())
        rows.append(r)
    write_csv(OUT / "margin_rule.csv", [{k: round(v, 4) for k, v in r.items()} for r in rows])
    return rows


# --------------------------------------------------------------------------- run
def score_matrix(retriever, queries):
    t0 = time.perf_counter()
    M = np.array([retriever.scores(q["query"]) for q in queries])
    return M, (time.perf_counter() - t0) * 1000 / len(queries)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    faqs, queries = load_faqs(), load_queries()
    cat_of = {f.id: f.category for f in faqs}
    y = np.array([int(q["expected_faq_id"]) if q["expected_faq_id"] != "NONE" else 0 for q in queries])
    qid = np.array([int(q["query_id"]) for q in queries])
    lang = np.array([q["lang"] for q in queries])
    dev, test, full = qid % 2 == 1, qid % 2 == 0, np.ones(len(queries), bool)
    print(f"FAQs: {len(faqs)}  queries: {len(queries)}  (tuning {dev.sum()}, held-out {test.sum()})")

    print("Scoring: keyword ...")
    K, k_ms = score_matrix(KeywordRetriever().fit(faqs), queries)
    print("Scoring: TF-IDF ...")
    T, t_ms = score_matrix(TfidfRetriever().fit(faqs), queries)
    print("Scoring: SBERT ...")
    sbert = SbertRetriever()
    sbert.fit(faqs)
    S, s_ms = score_matrix(sbert, queries)

    # ---- tune thresholds on the tuning split only
    th_k = tune_single(K, y, dev, cat_of)
    th_t = tune_single(T, y, dev, cat_of)
    th_s = tune_single(S, y, dev, cat_of)
    _, th_hs = tune_hybrid(T, S, y, dev, cat_of, [0.0])
    w_f, th_hf = tune_hybrid(T, S, y, dev, cat_of, FUSION_GRID)
    config = {
        "keyword": {"threshold": th_k},
        "tfidf": {"threshold": th_t},
        "sbert": {"threshold": th_s},
        "hybrid_spec": {"tfidf_threshold": SPEC_TFIDF_THRESHOLD, "fusion_weight": 0.0, "sbert_threshold": th_hs},
        "hybrid": {"tfidf_threshold": SPEC_TFIDF_THRESHOLD, "fusion_weight": w_f, "sbert_threshold": th_hf},
    }
    print("Tuned configuration:", json.dumps(config))

    preds = {
        "Keyword match": decide_single(K, th_k),
        "TF-IDF": decide_single(T, th_t),
        "SBERT": decide_single(S, th_s),
        "Hybrid (spec: TF-IDF -> SBERT)": decide_hybrid(T, S, SPEC_TFIDF_THRESHOLD, 0.0, th_hs)[0],
        "Hybrid (final: TF-IDF -> SBERT+fusion)": decide_hybrid(T, S, SPEC_TFIDF_THRESHOLD, w_f, th_hf)[0],
    }
    latency = {"Keyword match": k_ms, "TF-IDF": t_ms, "SBERT": s_ms}

    # ---- run the real production pipeline with the tuned config (latency + consistency check)
    print("Running production HybridRetriever ...")
    hybrid = HybridRetriever(tfidf_threshold=SPEC_TFIDF_THRESHOLD, sbert_threshold=th_hf, fusion_weight=w_f).fit(faqs)
    live, live_methods, live_ms, live_lang = [], [], [], []
    for q in queries:
        r = hybrid.retrieve(q["query"])
        live.append(r.faq_id or 0)
        live_methods.append(r.method)
        live_ms.append(r.elapsed_ms)
        live_lang.append(r.lang)
    live = np.array(live)
    mismatch = int((live != preds["Hybrid (final: TF-IDF -> SBERT+fusion)"]).sum())
    preds["Hybrid (final: TF-IDF -> SBERT+fusion)"] = live  # report the live pipeline's own answers
    live_ms = np.array(live_ms)
    latency["Hybrid (final: TF-IDF -> SBERT+fusion)"] = float(live_ms.mean())
    latency["Hybrid (spec: TF-IDF -> SBERT)"] = float("nan")
    lang_acc = float((np.array(live_lang) == lang).mean())

    # FR-02 / NF-02 category classifier (linear SVM) on in-scope queries
    clf = CategoryClassifier().fit(faqs)
    ins = y > 0
    cls_pred = np.array([clf.predict(q["query"]) for q in queries])
    cat_true = np.array([cat_of.get(v, "NONE") for v in y])
    clf_acc = float((cls_pred[ins] == cat_true[ins]).mean())
    svm = svm_report(cls_pred, cat_true, ins & test, lang)
    lang_counts = {lg: {"correct": int(((np.array(live_lang) == lang) & (lang == lg)).sum()),
                        "n": int((lang == lg).sum())} for lg in ("en", "ar")}
    sensitivity = sensitivity_table(T, S, y, dev, cat_of, th_hf, w_f)
    margins = margin_table(T, S, y, dev, test, w_f, th_hf)

    # ---- results tables
    rows = []
    for name, p in preds.items():
        for split, mask in (("held-out", test), ("full", full)):
            m = metrics(y, p, mask, cat_of)
            rows.append({"method": name, "split": split, **{k: round(v, 4) for k, v in m.items()},
                         "mean_latency_ms": round(latency.get(name, float("nan")), 1)})
    write_csv(OUT / "results_table.csv", rows)

    final = preds["Hybrid (final: TF-IDF -> SBERT+fusion)"]
    lang_rows, cat_rows = [], []
    for name, p in preds.items():
        for lg in ("en", "ar"):
            for split, mask in (("held-out", test), ("full", full)):
                mm = mask & (lang == lg)
                lang_rows.append({"method": name, "language": lg, "split": split, "n": int(mm.sum()),
                                  "accuracy": round(float((y[mm] == p[mm]).mean()), 4)})
        for c in CATEGORIES + ["NONE"]:
            mm = cat_true == c
            cat_rows.append({"method": name, "category": c, "n": int(mm.sum()),
                             "accuracy": round(float((y[mm] == p[mm]).mean()), 4)})
    write_csv(OUT / "per_language.csv", lang_rows)
    write_csv(OUT / "per_category.csv", cat_rows)

    var_rows = []
    variations = np.array([q["variation"] for q in queries])
    for v in sorted(set(variations)):
        mm = variations == v
        var_rows.append({"variation": v, "n": int(mm.sum()),
                         **{n: round(float((y[mm] == p[mm]).mean()), 4) for n, p in preds.items()}})
    write_csv(OUT / "per_variation.csv", var_rows)

    with open(OUT / "predictions_hybrid.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["query_id", "query", "lang", "expected_faq_id", "predicted_faq_id", "method", "correct",
                    "response_ms"])
        for i, q in enumerate(queries):
            w.writerow([q["query_id"], q["query"], q["lang"], q["expected_faq_id"], final[i] or "NONE",
                        live_methods[i], int(final[i] == y[i]), round(live_ms[i], 1)])

    method_mix = {m: int((np.array(live_methods) == m).sum()) for m in ("tfidf", "sbert", "fallback")}
    summary = {
        "config": config, "language_detection_accuracy": lang_acc, "language_detection_counts": lang_counts,
        "category_classifier_accuracy": clf_acc, "svm_held_out": svm,
        "tuning_sensitivity": sensitivity, "margin_rule": margins,
        "live_vs_simulated_mismatches": mismatch, "hybrid_method_mix": method_mix,
        "hybrid_latency_ms": {"mean": float(live_ms.mean()), "p95": float(np.percentile(live_ms, 95)),
                              "max": float(live_ms.max())},
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    plot_confusion(cat_true, np.array([cat_of.get(v, "NONE") for v in final]))
    plot_sweep(T, S, K, y, w_f, th_hf, cat_of)
    plot_comparison(rows)
    write_markdown(rows, lang_rows, cat_rows, var_rows, summary)
    print(open(OUT / "results.md", encoding="utf-8").read())


# --------------------------------------------------------------------------- output helpers
def write_csv(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def pct(v):
    return "–" if v != v else f"{v * 100:.1f}%"


def write_markdown(rows, lang_rows, cat_rows, var_rows, summary):
    L = ["# Retrieval evaluation results (NF-02)", "",
         "Generated by `python -m nlp.evaluate` — do not edit by hand.", "",
         "Tuning split = odd query ids (thresholds chosen here only); held-out split = even query ids.", "",
         "## Overall comparison", "",
         "| Method | Split | N | Accuracy | In-scope acc. | OOS rejection | Macro P | Macro R | Macro F1 | Category acc. | Mean ms/query |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['method']} | {r['split']} | {r['n']} | {pct(r['accuracy'])} | {pct(r['in_scope_accuracy'])} | "
                 f"{pct(r['oos_rejection'])} | {pct(r['precision_macro'])} | {pct(r['recall_macro'])} | "
                 f"{pct(r['f1_macro'])} | {pct(r['category_accuracy'])} | "
                 f"{'–' if r['mean_latency_ms'] != r['mean_latency_ms'] else r['mean_latency_ms']} |")
    L += ["", "## Accuracy by language", "", "| Method | Language | Split | N | Accuracy |", "|---|---|---|---|---|"]
    L += [f"| {r['method']} | {r['language']} | {r['split']} | {r['n']} | {pct(r['accuracy'])} |" for r in lang_rows]
    L += ["", "## Accuracy by category (full set)", "", "| Method | Category | N | Accuracy |", "|---|---|---|---|"]
    L += [f"| {r['method']} | {r['category']} | {r['n']} | {pct(r['accuracy'])} |" for r in cat_rows]
    names = [k for k in var_rows[0] if k not in ("variation", "n")]
    L += ["", "## Accuracy by query variation (full set)", "",
          "| Variation | N | " + " | ".join(names) + " |", "|---|---|" + "---|" * len(names)]
    L += [f"| {r['variation']} | {r['n']} | " + " | ".join(pct(r[n]) for n in names) + " |" for r in var_rows]
    s = summary
    L += ["", "## Other measurements", "",
          f"- Tuned configuration: `{json.dumps(s['config'])}`",
          f"- Language detection accuracy (FR-01): {pct(s['language_detection_accuracy'])}",
          "- Language detection counts: " + ", ".join(
              f"{g} {c['correct']}/{c['n']}" for g, c in s["language_detection_counts"].items()),
          f"- Category classifier (linear SVM) accuracy on all in-scope queries (FR-02): "
          f"{pct(s['category_classifier_accuracy'])}",
          "", "## NF-02: linear SVM category accuracy on the in-scope held-out queries", "",
          f"Overall: **{s['svm_held_out']['correct']}/{s['svm_held_out']['n']} = {pct(s['svm_held_out']['accuracy'])}** "
          "(target ≥ 85 %). Trained on FAQ questions (EN + AR) and keywords only.", "",
          "| Category | N | Correct | Accuracy (recall) | Precision | F1 |", "|---|---|---|---|---|---|"]
    L += [f"| {c['category']} | {c['n']} | {c['correct']} | {pct(c['recall'])} | {pct(c['precision'])} | {pct(c['f1'])} |"
          for c in s["svm_held_out"]["per_category"]]
    L += ["", "By language: " + ", ".join(f"{g} {v['correct']}/{v['n']}" for g, v in
                                          s["svm_held_out"]["per_language"].items()),
          "", "## Tuning-split sensitivity (one parameter varied, others at chosen values)", "",
          "| Parameter | Value | Accuracy | OOS rejection | Fallback rate |", "|---|---|---|---|---|"]
    L += [f"| {r['parameter']} | {r['value']} | {pct(r['accuracy'])} | {pct(r['oos_rejection'])} | {pct(r['fallback_rate'])} |"
          for r in s["tuning_sensitivity"]]
    L += ["", "## Clarification margin rule (analysis only, not adopted)", "",
          "| Margin | Tuning acc. | Tuning wrong answers | Held-out acc. | Held-out wrong answers | Held-out fallback |",
          "|---|---|---|---|---|---|"]
    L += [f"| {r['margin']:.2f} | {pct(r['tuning_accuracy'])} | {pct(r['tuning_wrong_answer_rate'])} | "
          f"{pct(r['held_out_accuracy'])} | {pct(r['held_out_wrong_answer_rate'])} | {pct(r['held_out_fallback_rate'])} |"
          for r in s["margin_rule"]]
    L += ["", "## Pipeline behaviour", "",
          f"- Hybrid answers by stage: {s['hybrid_method_mix']}",
          f"- Hybrid latency per query (ms): mean {s['hybrid_latency_ms']['mean']:.1f}, "
          f"p95 {s['hybrid_latency_ms']['p95']:.1f}, max {s['hybrid_latency_ms']['max']:.1f}",
          f"- Live pipeline vs simulated decisions mismatches: {s['live_vs_simulated_mismatches']}", "",
          "Figures: `confusion_matrix_hybrid.png`, `confusion_matrix_svm.png`, `threshold_sweep.png`, "
          "`method_comparison.png`."]
    (OUT / "results.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def _style():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.edgecolor": "#8a8984", "axes.labelcolor": "#2b2b2a", "xtick.color": "#52514e",
                         "ytick.color": "#52514e", "axes.grid": True, "grid.color": "#e6e5e0", "grid.linewidth": 0.6,
                         "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff"})
    return plt


BLUE, ORANGE, AQUA, GREY = "#2a78d6", "#eb6834", "#1baf7a", "#b9b8b2"


def plot_confusion(cat_true, cat_pred):
    plt = _style()
    labels = CATEGORIES + ["NONE"]
    M = np.zeros((len(labels), len(labels)), int)
    for t, p in zip(cat_true, cat_pred):
        M[labels.index(t), labels.index(p)] += 1
    fig, ax = plt.subplots(figsize=(8, 6.5))
    ax.grid(False)
    im = ax.imshow(M, cmap="Blues")
    short = ["Admissions", "Registration", "Fees", "Acad. Prog.", "Exams", "Stud. Serv.", "Fallback"]
    ax.set_xticks(range(len(labels)), short, rotation=35, ha="right")
    ax.set_yticks(range(len(labels)), short[:-1] + ["Out-of-scope"])
    for i in range(len(labels)):
        for j in range(len(labels)):
            if M[i, j]:
                ax.text(j, i, M[i, j], ha="center", va="center", fontsize=9,
                        color="white" if M[i, j] > M.max() * 0.55 else "#0b0b0b")
    ax.set_xlabel("Predicted category (category of returned FAQ)")
    ax.set_ylabel("Expected category")
    ax.set_title("Hybrid retriever — category confusion matrix (all 361 test queries)", loc="left")
    fig.colorbar(im, ax=ax, fraction=0.04)
    fig.tight_layout()
    fig.savefig(OUT / "confusion_matrix_hybrid.png", dpi=160)
    plt.close(fig)


def plot_svm_confusion(true, pred):
    plt = _style()
    M = np.zeros((len(CATEGORIES), len(CATEGORIES)), int)
    for t, p in zip(true, pred):
        M[CATEGORIES.index(t), CATEGORIES.index(p)] += 1
    fig, ax = plt.subplots(figsize=(7.5, 6))
    ax.grid(False)
    im = ax.imshow(M, cmap="Blues")
    short = ["Admissions", "Registration", "Fees", "Acad. Prog.", "Exams", "Stud. Serv."]
    ax.set_xticks(range(6), short, rotation=35, ha="right")
    ax.set_yticks(range(6), short)
    for i in range(6):
        for j in range(6):
            if M[i, j]:
                ax.text(j, i, M[i, j], ha="center", va="center", fontsize=9,
                        color="white" if M[i, j] > M.max() * 0.55 else "#0b0b0b")
    ax.set_xlabel("Predicted category (linear SVM)")
    ax.set_ylabel("Expected category")
    ax.set_title(f"Linear SVM — held-out in-scope queries (n = {len(true)})", loc="left")
    fig.colorbar(im, ax=ax, fraction=0.04)
    fig.tight_layout()
    fig.savefig(OUT / "confusion_matrix_svm.png", dpi=160)
    plt.close(fig)


def plot_sweep(T, S, K, y, w, sbert_th, cat_of):
    plt = _style()
    full = np.ones(len(y), bool)
    xs = np.round(np.arange(0.10, 0.901, 0.025), 3)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), sharey=True)

    acc_h, acc_t, fb = [], [], []
    for th in xs:
        m = metrics(y, decide_hybrid(T, S, th, w, sbert_th)[0], full, cat_of)
        acc_h.append(m["accuracy"]); fb.append(m["fallback_rate"])
        acc_t.append(metrics(y, decide_single(T, th), full, cat_of)["accuracy"])
    for a in axes:
        a.axvspan(0.5, 0.9, color="#f1f0ec", zorder=0)
    axes[0].text(0.505, 1.0, "0.5–0.9 range", color="#8a8984", fontsize=8, va="top")
    ax = axes[0]
    ax.plot(xs, acc_h, color=BLUE, lw=2, marker="o", ms=4, label="Hybrid accuracy")
    ax.plot(xs, acc_t, color=ORANGE, lw=2, marker="o", ms=4, label="TF-IDF-only accuracy")
    ax.plot(xs, fb, color=AQUA, lw=2, ls="--", label="Hybrid fallback rate")
    ax.axvline(SPEC_TFIDF_THRESHOLD, color=GREY, lw=1)
    ax.text(SPEC_TFIDF_THRESHOLD + 0.005, 0.03, "0.75 (default)", color="#52514e", fontsize=8)
    ax.set_xlabel("TF-IDF confidence threshold")
    ax.set_ylabel("Proportion of test queries")
    ax.set_title("A. TF-IDF threshold sweep", loc="left")
    ax.legend(frameon=False, fontsize=8, loc="center left")

    acc2, oos2, fb2 = [], [], []
    for th in xs:
        m = metrics(y, decide_hybrid(T, S, SPEC_TFIDF_THRESHOLD, w, th)[0], full, cat_of)
        acc2.append(m["accuracy"]); oos2.append(m["oos_rejection"]); fb2.append(m["fallback_rate"])
    ax = axes[1]
    ax.plot(xs, acc2, color=BLUE, lw=2, marker="o", ms=4, label="Hybrid accuracy")
    ax.plot(xs, oos2, color=ORANGE, lw=2, marker="o", ms=4, label="Out-of-scope rejection")
    ax.plot(xs, fb2, color=AQUA, lw=2, ls="--", label="Fallback rate")
    if xs[0] <= sbert_th <= xs[-1]:
        ax.axvline(sbert_th, color=GREY, lw=1)
        ax.text(sbert_th + 0.005, 0.03, f"{sbert_th:.2f} (tuned)", color="#52514e", fontsize=8)
    ax.set_xlabel("SBERT-stage (fused) threshold")
    ax.set_title("B. SBERT-stage threshold sweep", loc="left")
    ax.legend(frameon=False, fontsize=8, loc="center left")
    ax.set_ylim(0, 1.02)
    fig.tight_layout()
    fig.savefig(OUT / "threshold_sweep.png", dpi=160)
    plt.close(fig)


def plot_comparison(rows):
    plt = _style()
    data = [r for r in rows if r["split"] == "held-out"]
    labels = {"Hybrid (spec: TF-IDF -> SBERT)": "Hybrid (spec)\nTF-IDF -> SBERT",
              "Hybrid (final: TF-IDF -> SBERT+fusion)": "Hybrid (final)\nTF-IDF -> SBERT+fusion"}
    names = [labels.get(r["method"], r["method"]) for r in data]
    vals = [r["accuracy"] for r in data]
    fig, ax = plt.subplots(figsize=(9, 4.4))
    colors = [BLUE if "final" in r["method"] else GREY for r in data]
    bars = ax.bar(range(len(vals)), vals, color=colors, width=0.6, edgecolor="white", linewidth=2)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.025, f"{v * 100:.1f}%", ha="center", fontsize=9, color="#2b2b2a")
    ax.axhline(0.85, color=ORANGE, lw=1.5, ls="--")
    ax.text(-0.45, 0.865, "NF-02 target 85%", color="#52514e", fontsize=8, ha="left")
    ax.set_xticks(range(len(vals)), names, fontsize=8)
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("Accuracy (held-out split)")
    ax.set_title("Retrieval accuracy by method — held-out split", loc="left")
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(OUT / "method_comparison.png", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    main()

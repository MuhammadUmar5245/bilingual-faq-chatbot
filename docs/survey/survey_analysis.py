"""Descriptive analysis of the usability questionnaire (Chapter 5.3, NF-03).

Usage:  python docs/survey/survey_analysis.py docs/survey/survey_responses.csv
Input:  a CSV with the columns of survey_responses_template.csv (one row per respondent).
Output: docs/survey/results/ - summary.md, item_statistics.csv, likert_chart.png, groups_chart.png

This script only analyses real responses. It never generates or fills in data.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"

ITEMS = {
    "Q1": "The chatbot was easy to use",
    "Q2": "Could start a conversation without help",
    "Q3": "Topic buttons / popular questions helped",
    "Q4": "Answers matched my questions",
    "Q5": "Answers were clear and complete",
    "Q6": "Fallback contact details were useful",
    "Q7": "The chatbot answered quickly",
    "Q8": "Faster than website search / email",
    "Q9": "Understood my questions in Arabic",
    "Q10": "Arabic RTL interface displayed correctly",
    "Q11": "Worked well on my mobile phone",
    "Q12": "Design is clear and professional",
    "Q13": "Overall satisfied",
    "Q14": "Would use the chatbot again",
    "Q15": "Would recommend it to other students",
    "S1": "Staff: could add/edit an FAQ without help",
    "S2": "Staff: statistics / unanswered list useful",
}
CONSTRUCTS = {
    "Ease of use": ["Q1", "Q2", "Q3"],
    "Perceived accuracy": ["Q4", "Q5", "Q6"],
    "Speed": ["Q7", "Q8"],
    "Arabic support": ["Q9", "Q10"],
    "Interface": ["Q11", "Q12"],
    "Satisfaction and intent to reuse": ["Q13", "Q14", "Q15"],
}
GROUPS = {"student": "Current students", "applicant": "Prospective students", "staff": "Administration staff"}


def cronbach_alpha(df: pd.DataFrame) -> float:
    df = df.dropna()
    k = df.shape[1]
    if k < 2 or len(df) < 2:
        return float("nan")
    item_var = df.var(axis=0, ddof=1).sum()
    total_var = df.sum(axis=1).var(ddof=1)
    return float(k / (k - 1) * (1 - item_var / total_var)) if total_var > 0 else float("nan")


def main(path):
    df = pd.read_csv(path)
    if df.empty:
        sys.exit("The responses file has no rows. Collect responses first - this script does not create data.")
    for c in list(ITEMS) + ["E1"]:
        df[c] = pd.to_numeric(df.get(c), errors="coerce")
        bad = df[c].dropna()
        if ((bad < 1) | (bad > 5)).any():
            sys.exit(f"Column {c} has values outside 1-5")
    OUT.mkdir(parents=True, exist_ok=True)

    rows = []
    for c, label in ITEMS.items():
        s = df[c].dropna()
        if s.empty:
            continue
        rows.append({"item": c, "statement": label, "n": len(s), "mean": round(s.mean(), 2),
                     "median": s.median(), "sd": round(s.std(ddof=1), 2) if len(s) > 1 else np.nan,
                     "pct_agree": round((s >= 4).mean() * 100, 1), "pct_disagree": round((s <= 2).mean() * 100, 1)})
    items = pd.DataFrame(rows)
    items.to_csv(OUT / "item_statistics.csv", index=False)

    e1 = df["E1"].dropna()
    nf03 = (e1 >= 4).mean() * 100 if len(e1) else float("nan")

    lines = ["# Survey results", "", f"Source file: `{Path(path).name}` — {len(df)} respondents", "",
             "## Respondents", "", "| Group | n |", "|---|---|"]
    for g, label in GROUPS.items():
        lines.append(f"| {label} | {(df['group'] == g).sum()} |")
    lines += ["", "## NF-03 — overall ease of use (E1)", "",
              f"- Respondents rating the interface **Easy or Very easy**: **{nf03:.1f} %** (n = {len(e1)})",
              f"- Target ≥ 80 % → **{'MET' if nf03 >= 80 else 'NOT MET'}**", "",
              "## Item statistics", "", "| Item | Statement | n | Mean | Median | SD | % agree (4–5) |",
              "|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['item']} | {r['statement']} | {r['n']} | {r['mean']} | {r['median']} | {r['sd']} | {r['pct_agree']} % |")
    lines += ["", "## Constructs", "", "| Construct | Items | Mean | Cronbach's α |", "|---|---|---|---|"]
    for name, cols in CONSTRUCTS.items():
        sub = df[cols]
        alpha = cronbach_alpha(sub)
        lines.append(f"| {name} | {', '.join(cols)} | {sub.stack().mean():.2f} | {'–' if np.isnan(alpha) else f'{alpha:.2f}'} |")
    lines += ["", "## Mean score by respondent group", "", "| Construct | " + " | ".join(GROUPS.values()) + " |",
              "|---|" + "---|" * len(GROUPS)]
    for name, cols in CONSTRUCTS.items():
        vals = []
        for g in GROUPS:
            sub = df.loc[df["group"] == g, cols].stack()
            vals.append("–" if sub.empty else f"{sub.mean():.2f}")
        lines.append(f"| {name} | " + " | ".join(vals) + " |")
    for col, title in (("O1", "What respondents liked (O1)"), ("O2", "Suggested improvements (O2)")):
        answers = [str(a).strip() for a in df.get(col, pd.Series(dtype=str)).dropna() if str(a).strip()]
        lines += ["", f"## {title}", ""] + [f"- {a}" for a in answers] if answers else ["", f"## {title}", "", "_No answers._"]
    lines += ["", "Charts: `likert_chart.png`, `groups_chart.png`"]
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    plot_likert(df, rows)
    plot_groups(df)
    print("\n".join(lines[:16]))
    print(f"\nWritten to {OUT}")


def plot_likert(df, rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    # Diverging palette: two hues with a neutral grey midpoint
    colors = ["#c4442f", "#eba08f", "#c9c8c2", "#8fb7e8", "#2a6fc4"]
    labels = ["Strongly disagree", "Disagree", "Neutral", "Agree", "Strongly agree"]
    items = [r["item"] for r in rows]
    fig, ax = plt.subplots(figsize=(10, 0.42 * len(items) + 1.6))
    for y, item in enumerate(items):
        s = df[item].dropna()
        shares = [(s == v).mean() * 100 for v in range(1, 6)]
        left = -(shares[0] + shares[1] + shares[2] / 2)
        for v, share in enumerate(shares):
            ax.barh(y, share, left=left, color=colors[v], edgecolor="white", linewidth=1.5, height=0.7,
                    label=labels[v] if y == 0 else None)
            left += share
    ax.axvline(0, color="#52514e", lw=1)
    ax.set_yticks(range(len(items)), [f"{r['item']}  {r['statement']}" for r in rows], fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlabel("% of respondents (centred on neutral)")
    ax.set_title("Likert responses by item", loc="left")
    ax.legend(ncol=5, fontsize=8, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "likert_chart.png", dpi=160)
    plt.close(fig)


def plot_groups(df):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    names = list(CONSTRUCTS)
    colors = ["#2a78d6", "#eb6834", "#1baf7a"]
    fig, ax = plt.subplots(figsize=(10, 4.2))
    width = 0.26
    for i, (g, label) in enumerate(GROUPS.items()):
        means = [df.loc[df["group"] == g, cols].stack().mean() for cols in CONSTRUCTS.values()]
        ax.bar(np.arange(len(names)) + (i - 1) * width, means, width, color=colors[i], label=label,
               edgecolor="white", linewidth=2)
    ax.set_xticks(range(len(names)), [n.replace(" and ", " &\n") for n in names], fontsize=8.5)
    ax.set_ylim(1, 5)
    ax.set_ylabel("Mean score (1–5)")
    ax.set_title("Mean construct score by respondent group", loc="left")
    ax.legend(frameon=False, fontsize=8)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "groups_chart.png", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])

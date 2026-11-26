import { useEffect, useState } from "react";
import { api, errorMessage } from "../api.js";
import { BarList, ColumnChart, ShareBar } from "../components/charts.jsx";

const pct = (v) => (v === null || v === undefined ? "–" : `${(v * 100).toFixed(1)}%`);

export default function Overview({ navigate }) {
  const [stats, setStats] = useState(null);
  const [days, setDays] = useState(14);
  const [error, setError] = useState("");

  useEffect(() => {
    api.stats(days).then(setStats).catch((e) => setError(errorMessage(e)));
  }, [days]);

  if (error) return <div className="alert error">{error}</div>;
  if (!stats) return <p className="muted">Loading statistics…</p>;

  const perDay = stats.per_day.map((d) => {
    const date = new Date(`${d.date}T00:00:00`);
    return {
      label: date.toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" }),
      short: date.toLocaleDateString(undefined, { day: "numeric", month: "short" }),
      value: d.count,
    };
  });
  const cats = Object.entries(stats.per_category)
    .map(([label, value]) => ({ label, value }))
    .sort((a, b) => b.value - a.value);

  const kpis = [
    { label: "Total queries", value: stats.total_queries.toLocaleString(), note: `${stats.sessions} chat sessions` },
    { label: "Resolution rate", value: pct(stats.resolution_rate), note: `${stats.fallback} sent to fallback` },
    { label: "Avg. confidence", value: pct(stats.avg_confidence), note: "answered queries" },
    {
      label: "Avg. response time",
      value: `${Math.round(stats.avg_response_ms)} ms`,
      note: stats.avg_response_ms < 2000 ? "within 2 s target (FR-04)" : "above 2 s target",
    },
    { label: "Helpful feedback", value: pct(stats.helpful_rate), note: `${stats.feedback_total} ratings` },
    { label: "Active FAQs", value: stats.faqs_active, note: `${stats.faqs_inactive} disabled` },
  ];

  return (
    <div className="stack">
      <div className="kpis">
        {kpis.map((k) => (
          <div className="kpi" key={k.label}>
            <div className="kpi-label">{k.label}</div>
            <div className="kpi-value">{k.value}</div>
            <div className="kpi-note">{k.note}</div>
          </div>
        ))}
      </div>

      <div className="grid-2">
        <section className="card span-2">
          <div className="card-head">
            <h2>Queries per day</h2>
            <select value={days} onChange={(e) => setDays(Number(e.target.value))} aria-label="Date range">
              <option value={7}>Last 7 days</option>
              <option value={14}>Last 14 days</option>
              <option value={30}>Last 30 days</option>
            </select>
          </div>
          <ColumnChart data={perDay} />
        </section>

        <section className="card">
          <div className="card-head">
            <h2>Queries by category</h2>
          </div>
          <BarList data={cats} total={stats.total_queries} />
        </section>

        <section className="card">
          <div className="card-head">
            <h2>How queries were answered</h2>
          </div>
          <ShareBar
            data={["tfidf", "sbert", "fallback"].map((k) => ({ key: k, value: stats.per_method[k] || 0 }))}
            labels={{ tfidf: "TF-IDF match", sbert: "SBERT (semantic) match", fallback: "Fallback" }}
          />
          <h3 className="sub">Query language</h3>
          <ShareBar
            data={["en", "ar"].map((k) => ({ key: k, value: stats.per_language[k] || 0 }))}
            labels={{ en: "English", ar: "Arabic" }}
          />
        </section>

        <section className="card span-2">
          <div className="card-head">
            <h2>Most asked FAQs</h2>
            <button className="btn small" onClick={() => navigate("unanswered")}>
              View unanswered queries →
            </button>
          </div>
          <BarList data={stats.top_faqs.map((f) => ({ label: `#${f.id} ${f.question}`, value: f.count }))} unit="matches" />
        </section>
      </div>
    </div>
  );
}

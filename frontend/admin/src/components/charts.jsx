import { useState } from "react";

/* Lightweight SVG charts with hover tooltips (no chart library needed). */

export function ColumnChart({ data, height = 220, label = "Queries" }) {
  const [hover, setHover] = useState(null);
  const W = 1000, H = height, pad = { l: 34, r: 8, t: 12, b: 28 };
  const max = Math.max(1, ...data.map((d) => d.value));
  const step = Math.pow(10, Math.floor(Math.log10(max)));
  const niceMax = Math.ceil(max / step) * step;
  const ticks = [0, niceMax / 2, niceMax];
  const bw = (W - pad.l - pad.r) / data.length;
  const y = (v) => pad.t + (H - pad.t - pad.b) * (1 - v / niceMax);
  const labelEvery = Math.ceil(data.length / 7);
  return (
    <div className="chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${label} per day`}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={pad.l} x2={W - pad.r} y1={y(t)} y2={y(t)} className="grid" />
            <text x={pad.l - 6} y={y(t) + 4} textAnchor="end" className="axis">
              {Math.round(t)}
            </text>
          </g>
        ))}
        {data.map((d, i) => {
          const x = pad.l + i * bw;
          const bh = Math.max(d.value ? 2 : 0, H - pad.b - y(d.value));
          return (
            <g key={d.label} onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)}>
              <rect x={x} y={pad.t} width={bw} height={H - pad.t - pad.b} fill="transparent" />
              <rect
                x={x + bw * 0.18}
                y={H - pad.b - bh}
                width={bw * 0.64}
                height={bh}
                rx="3"
                className={`bar ${hover === i ? "hover" : ""}`}
              />
              {i % labelEvery === 0 && (
                <text x={x + bw / 2} y={H - 9} textAnchor="middle" className="axis">
                  {d.short}
                </text>
              )}
            </g>
          );
        })}
        <line x1={pad.l} x2={W - pad.r} y1={H - pad.b} y2={H - pad.b} className="baseline" />
      </svg>
      {hover !== null && (
        <div className="tooltip" style={{ left: `${((pad.l + (hover + 0.5) * bw) / W) * 100}%` }}>
          <strong>{data[hover].label}</strong>
          <span>
            {label}: {data[hover].value}
          </span>
        </div>
      )}
    </div>
  );
}

export function BarList({ data, total, unit = "queries" }) {
  const max = Math.max(1, ...data.map((d) => d.value));
  return (
    <ul className="barlist">
      {data.map((d) => (
        <li key={d.label} title={`${d.label}: ${d.value} ${unit}${total ? ` (${Math.round((d.value / total) * 100)}%)` : ""}`}>
          <div className="barlist-row">
            <span>{d.label}</span>
            <span className="num">
              {d.value}
              {total ? <span className="muted"> · {Math.round((d.value / total) * 100)}%</span> : null}
            </span>
          </div>
          <div className="barlist-track">
            <div className="barlist-fill" style={{ width: `${(d.value / max) * 100}%` }} />
          </div>
        </li>
      ))}
      {data.length === 0 && <li className="muted">No data yet.</li>}
    </ul>
  );
}

const SHARE_COLORS = { tfidf: "#2a78d6", sbert: "#1baf7a", fallback: "#eb6834", en: "#2a78d6", ar: "#1baf7a" };

export function ShareBar({ data, labels = {} }) {
  const total = data.reduce((s, d) => s + d.value, 0);
  if (!total) return <p className="muted">No data yet.</p>;
  return (
    <div>
      <div className="sharebar" role="img" aria-label="share">
        {data.map((d) =>
          d.value ? (
            <div
              key={d.key}
              title={`${labels[d.key] || d.key}: ${d.value} (${Math.round((d.value / total) * 100)}%)`}
              style={{ flex: d.value, background: SHARE_COLORS[d.key] || "#8a8984" }}
            />
          ) : null
        )}
      </div>
      <ul className="legend">
        {data.map((d) => (
          <li key={d.key}>
            <i style={{ background: SHARE_COLORS[d.key] || "#8a8984" }} />
            {labels[d.key] || d.key} <strong>{d.value}</strong>
            <span className="muted"> ({Math.round((d.value / total) * 100)}%)</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

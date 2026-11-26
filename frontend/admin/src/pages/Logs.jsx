import { useEffect, useState } from "react";
import { api, errorMessage } from "../api.js";
import { MethodBadge, Pagination, fmtDate, useToast } from "../components/ui.jsx";

export default function Logs() {
  const [filters, setFilters] = useState({ q: "", method: "", lang: "", date_from: "", date_to: "", page: 1 });
  const [search, setSearch] = useState("");
  const [data, setData] = useState(null);
  const toast = useToast();

  useEffect(() => {
    const p = { page: filters.page, per_page: 20 };
    for (const k of ["q", "method", "lang", "date_from", "date_to"]) if (filters[k]) p[k] = filters[k];
    api.logs(p).then(setData).catch((e) => toast(errorMessage(e), "error"));
  }, [filters, toast]);

  useEffect(() => {
    const t = setTimeout(() => setFilters((f) => (f.q === search ? f : { ...f, q: search, page: 1 })), 300);
    return () => clearTimeout(t);
  }, [search]);

  const set = (k) => (e) => setFilters({ ...filters, [k]: e.target.value, page: 1 });

  return (
    <div className="stack">
      <div className="toolbar">
        <input className="search" placeholder="Search query text…" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search logs" />
        <select value={filters.method} onChange={set("method")} aria-label="Method">
          <option value="">All methods</option>
          <option value="tfidf">TF-IDF</option>
          <option value="sbert">SBERT</option>
          <option value="fallback">Fallback</option>
        </select>
        <select value={filters.lang} onChange={set("lang")} aria-label="Language">
          <option value="">All languages</option>
          <option value="en">English</option>
          <option value="ar">Arabic</option>
        </select>
        <label className="inline">
          From <input type="date" value={filters.date_from} onChange={set("date_from")} />
        </label>
        <label className="inline">
          To <input type="date" value={filters.date_to} onChange={set("date_to")} />
        </label>
      </div>
      <section className="card flush">
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th style={{ width: 150 }}>Time</th>
                <th>Query</th>
                <th>Matched FAQ</th>
                <th style={{ width: 60 }}>Lang</th>
                <th style={{ width: 90 }}>Method</th>
                <th style={{ width: 90 }}>Confidence</th>
                <th style={{ width: 80 }}>ms</th>
                <th style={{ width: 80 }}>Rating</th>
                <th style={{ width: 90 }}>Session</th>
              </tr>
            </thead>
            <tbody>
              {data?.items.map((l) => (
                <tr key={l.id}>
                  <td className="muted small">{fmtDate(l.created_at)}</td>
                  <td dir="auto">{l.query_text}</td>
                  <td className="small">{l.matched_faq_id ? `#${l.matched_faq_id} ${l.matched_question || ""}` : <span className="muted">—</span>}</td>
                  <td>{l.detected_lang.toUpperCase()}</td>
                  <td>
                    <MethodBadge method={l.method} />
                  </td>
                  <td>{(l.confidence * 100).toFixed(1)}%</td>
                  <td className="muted">{Math.round(l.response_ms)}</td>
                  <td>{l.helpful === null ? <span className="muted">—</span> : l.helpful ? "👍" : "👎"}</td>
                  <td className="muted small mono" title={l.session_id}>
                    {l.session_id.slice(0, 8)}
                  </td>
                </tr>
              ))}
              {data && data.items.length === 0 && (
                <tr>
                  <td colSpan={9} className="empty">
                    No conversations match these filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {data && <Pagination {...data} onPage={(page) => setFilters({ ...filters, page })} />}
      </section>
    </div>
  );
}

import { useEffect, useState } from "react";
import { api, errorMessage } from "../api.js";
import { Pagination, fmtDate, useToast } from "../components/ui.jsx";

export default function Unanswered({ navigate }) {
  const [type, setType] = useState("all");
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const toast = useToast();

  useEffect(() => {
    api
      .unanswered({ type, page, per_page: 20 })
      .then(setData)
      .catch((e) => toast(errorMessage(e), "error"));
  }, [type, page, toast]);

  return (
    <div className="stack">
      <p className="muted">
        Queries the chatbot could not answer (fallback) or that students rated as not helpful. Use them to add new FAQs so the
        knowledge base keeps improving.
      </p>
      <div className="toolbar">
        <div className="segmented" role="tablist">
          {[
            ["all", "All"],
            ["fallback", "No answer (fallback)"],
            ["unhelpful", "Rated not helpful"],
          ].map(([k, label]) => (
            <button
              key={k}
              role="tab"
              aria-selected={type === k}
              className={type === k ? "active" : ""}
              onClick={() => {
                setType(k);
                setPage(1);
              }}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      <section className="card flush">
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th style={{ width: 150 }}>Time</th>
                <th>Student query</th>
                <th style={{ width: 150 }}>Reason</th>
                <th style={{ width: 160 }}>Predicted category</th>
                <th style={{ width: 90 }}>Best score</th>
                <th style={{ width: 170 }}></th>
              </tr>
            </thead>
            <tbody>
              {data?.items.map((l) => (
                <tr key={l.id}>
                  <td className="muted small">{fmtDate(l.created_at)}</td>
                  <td dir="auto">{l.query_text}</td>
                  <td>
                    <span className={`badge ${l.reason === "fallback" ? "m-fallback" : "off"}`}>
                      {l.reason === "fallback" ? "No answer" : "Not helpful"}
                    </span>
                  </td>
                  <td className="small">{l.category || "—"}</td>
                  <td>{(l.confidence * 100).toFixed(1)}%</td>
                  <td>
                    <button className="btn small primary" onClick={() => navigate("faqs", { new: l.query_text })}>
                      Create FAQ from this
                    </button>
                  </td>
                </tr>
              ))}
              {data && data.items.length === 0 && (
                <tr>
                  <td colSpan={6} className="empty">
                    Nothing here — every query was answered.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {data && <Pagination {...data} onPage={setPage} />}
      </section>
    </div>
  );
}

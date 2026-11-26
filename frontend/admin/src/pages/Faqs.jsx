import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "../api.js";
import { Confirm, Modal, Pagination, fmtDate, useToast } from "../components/ui.jsx";

const ARABIC = /[؀-ۿ]/;
const EMPTY = { question_en: "", question_ar: "", answer: "", answer_ar: "", category_id: "", keywords: "", is_active: true };

/* ------------------------------------------------------------- add / edit form (FR-06) */
export function FaqForm({ initial, categories, onSaved, onClose }) {
  const [form, setForm] = useState({ ...EMPTY, ...initial });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const body = {
      question_en: form.question_en,
      question_ar: form.question_ar,
      answer: form.answer,
      answer_ar: form.answer_ar,
      keywords: form.keywords,
      category_id: Number(form.category_id),
      is_active: form.is_active,
    };
    try {
      const saved = initial?.id ? await api.updateFaq(initial.id, body) : await api.createFaq(body);
      toast(initial?.id ? `FAQ #${saved.id} updated — chatbot index rebuilt` : `FAQ #${saved.id} added — chatbot index rebuilt`);
      onSaved(saved);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal title={initial?.id ? `Edit FAQ #${initial.id}` : "Add new FAQ"} onClose={onClose} wide>
      <form className="form" onSubmit={submit}>
        {error && <div className="alert error">{error}</div>}
        <div className="form-grid">
          <label>
            Question (English) *
            <input value={form.question_en} onChange={set("question_en")} required maxLength={4000} />
          </label>
          <label>
            Question (Arabic)
            <input value={form.question_ar} onChange={set("question_ar")} dir="rtl" lang="ar" maxLength={4000} />
          </label>
          <label>
            Answer (English) *
            <textarea value={form.answer} onChange={set("answer")} rows={5} required maxLength={4000} />
          </label>
          <label>
            Answer (Arabic)
            <textarea value={form.answer_ar} onChange={set("answer_ar")} rows={5} dir="rtl" lang="ar" maxLength={4000} />
          </label>
          <label>
            Category *
            <select value={form.category_id} onChange={set("category_id")} required>
              <option value="">Select a category…</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name_en} — {c.name_ar}
                </option>
              ))}
            </select>
          </label>
          <label>
            Keywords / synonyms (comma separated, English or Arabic)
            <input value={form.keywords} onChange={set("keywords")} placeholder="e.g. fees, tuition, الرسوم" />
          </label>
        </div>
        <label className="check">
          <input type="checkbox" checked={form.is_active} onChange={set("is_active")} /> Active (visible to the chatbot)
        </label>
        <div className="form-actions">
          <button type="button" className="btn" onClick={onClose}>
            Cancel
          </button>
          <button className="btn primary" disabled={busy}>
            {busy ? "Saving…" : "Save FAQ"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

/* ------------------------------------------------------------- CSV import */
function ImportDialog({ onClose, onDone }) {
  const [file, setFile] = useState(null);
  const [mode, setMode] = useState("append");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const r = await api.importFaqs(file, mode);
      setResult(r);
      onDone();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal title="Import FAQs from CSV" onClose={onClose}>
      <form className="form" onSubmit={submit}>
        <p className="muted">
          Columns: <code>question_en, question_ar, answer, answer_ar, category, keywords</code> (only{" "}
          <code>question_en</code>, <code>answer</code> and <code>category</code> are required). UTF-8, max 5 MB.
        </p>
        {error && <div className="alert error">{error}</div>}
        {result && (
          <div className="alert ok">
            Imported {result.imported} FAQ(s), skipped {result.skipped}.
            {result.errors?.length > 0 && (
              <ul>
                {result.errors.map((e) => (
                  <li key={e}>{e}</li>
                ))}
              </ul>
            )}
          </div>
        )}
        <label>
          CSV file
          <input type="file" accept=".csv,text/csv" onChange={(e) => setFile(e.target.files[0])} required />
        </label>
        <fieldset className="radio-row">
          <label className="check">
            <input type="radio" name="mode" checked={mode === "append"} onChange={() => setMode("append")} /> Add to existing FAQs
          </label>
          <label className="check">
            <input type="radio" name="mode" checked={mode === "replace"} onChange={() => setMode("replace")} /> Replace (disable
            all existing FAQs first)
          </label>
        </fieldset>
        <div className="form-actions">
          <button type="button" className="btn" onClick={onClose}>
            Close
          </button>
          <button className="btn primary" disabled={busy || !file}>
            {busy ? "Importing…" : "Import"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

/* ------------------------------------------------------------- page */
export default function Faqs({ params, navigate }) {
  const [categories, setCategories] = useState([]);
  const [filters, setFilters] = useState({ q: "", category_id: "", status: "", page: 1 });
  const [search, setSearch] = useState("");
  const [data, setData] = useState(null);
  const [editing, setEditing] = useState(null);
  const [confirm, setConfirm] = useState(null);
  const [importing, setImporting] = useState(false);
  const [expanded, setExpanded] = useState(null);
  const toast = useToast();

  useEffect(() => {
    api.categories().then(setCategories);
  }, []);

  // "Create FAQ from this" on the Unanswered page links here with ?new=<query>
  useEffect(() => {
    if (params.new) {
      const text = params.new;
      setEditing(ARABIC.test(text) ? { question_ar: text } : { question_en: text });
      navigate("faqs");
    }
  }, [params.new, navigate]);

  const load = useCallback(() => {
    const p = { page: filters.page, per_page: 15 };
    if (filters.q) p.q = filters.q;
    if (filters.category_id) p.category_id = filters.category_id;
    if (filters.status) p.status = filters.status;
    api.faqs(p).then(setData).catch((e) => toast(errorMessage(e), "error"));
  }, [filters, toast]);

  useEffect(load, [load]);

  useEffect(() => {
    const t = setTimeout(() => setFilters((f) => (f.q === search ? f : { ...f, q: search, page: 1 })), 300);
    return () => clearTimeout(t);
  }, [search]);

  async function toggle(f) {
    try {
      const r = await api.toggleFaq(f.id);
      toast(`FAQ #${f.id} ${r.is_active ? "enabled" : "disabled"}`);
      load();
    } catch (e) {
      toast(errorMessage(e), "error");
    }
  }

  async function remove(f) {
    try {
      await api.deleteFaq(f.id);
      toast(`FAQ #${f.id} deleted`);
      setConfirm(null);
      load();
    } catch (e) {
      toast(errorMessage(e), "error");
    }
  }

  return (
    <div className="stack">
      <div className="toolbar">
        <input
          className="search"
          placeholder="Search questions, answers, keywords…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Search FAQs"
        />
        <select value={filters.category_id} onChange={(e) => setFilters({ ...filters, category_id: e.target.value, page: 1 })} aria-label="Category">
          <option value="">All categories</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name_en}
            </option>
          ))}
        </select>
        <select value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value, page: 1 })} aria-label="Status">
          <option value="">All statuses</option>
          <option value="active">Active</option>
          <option value="inactive">Disabled</option>
        </select>
        <div className="spacer" />
        <a className="btn" href={api.exportUrl}>
          Export CSV
        </a>
        <button className="btn" onClick={() => setImporting(true)}>
          Import CSV
        </button>
        <button className="btn primary" onClick={() => setEditing({})}>
          + Add FAQ
        </button>
      </div>

      <section className="card flush">
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th style={{ width: 56 }}>#</th>
                <th>Question</th>
                <th style={{ width: 160 }}>Category</th>
                <th style={{ width: 100 }}>Status</th>
                <th style={{ width: 140 }}>Updated</th>
                <th style={{ width: 210 }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {data?.items.map((f) => (
                <tr key={f.id} className={f.is_active ? "" : "inactive"}>
                  <td className="muted">{f.id}</td>
                  <td>
                    <button className="link" onClick={() => setExpanded(expanded === f.id ? null : f.id)}>
                      {f.question_en}
                    </button>
                    {f.question_ar && (
                      <div className="ar" dir="rtl">
                        {f.question_ar}
                      </div>
                    )}
                    {expanded === f.id && (
                      <div className="answer-preview">
                        <p>{f.answer}</p>
                        {f.answer_ar && <p dir="rtl">{f.answer_ar}</p>}
                        {f.keywords && <p className="muted small">Keywords: {f.keywords}</p>}
                      </div>
                    )}
                  </td>
                  <td>
                    <span className="badge cat">{f.category}</span>
                  </td>
                  <td>
                    <span className={`badge ${f.is_active ? "ok" : "off"}`}>{f.is_active ? "Active" : "Disabled"}</span>
                  </td>
                  <td className="muted small">{fmtDate(f.updated_at)}</td>
                  <td className="actions">
                    <div>
                    <button className="btn small" onClick={() => setEditing(f)}>
                      Edit
                    </button>
                    <button className="btn small" onClick={() => toggle(f)}>
                      {f.is_active ? "Disable" : "Enable"}
                    </button>
                    <button className="btn small danger-outline" onClick={() => setConfirm(f)}>
                      Delete
                    </button>
                    </div>
                  </td>
                </tr>
              ))}
              {data && data.items.length === 0 && (
                <tr>
                  <td colSpan={6} className="empty">
                    No FAQs match these filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {data && <Pagination {...data} onPage={(page) => setFilters({ ...filters, page })} />}
      </section>

      {editing && (
        <FaqForm
          initial={editing}
          categories={categories}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            load();
          }}
        />
      )}
      {importing && <ImportDialog onClose={() => setImporting(false)} onDone={load} />}
      {confirm && (
        <Confirm
          title="Delete FAQ"
          message={`Permanently delete FAQ #${confirm.id} "${confirm.question_en}"? Consider disabling it instead to keep its history.`}
          confirmLabel="Delete"
          danger
          onConfirm={() => remove(confirm)}
          onClose={() => setConfirm(null)}
        />
      )}
    </div>
  );
}

import { useEffect, useState } from "react";
import { api, errorMessage } from "../api.js";
import { useToast } from "../components/ui.jsx";

function Threshold({ label, help, value, onChange }) {
  return (
    <label className="threshold">
      <div className="threshold-head">
        <span>{label}</span>
        <strong>{Number(value).toFixed(2)}</strong>
      </div>
      <input type="range" min="0" max="1" step="0.01" value={value} onChange={(e) => onChange(e.target.value)} />
      <span className="muted small">{help}</span>
    </label>
  );
}

export default function Settings() {
  const [s, setS] = useState(null);
  const [pw, setPw] = useState({ current: "", next: "", confirm: "" });
  const [pwError, setPwError] = useState("");
  const toast = useToast();

  useEffect(() => {
    api.settings().then(setS).catch((e) => toast(errorMessage(e), "error"));
  }, [toast]);

  async function save(e) {
    e.preventDefault();
    try {
      const body = {
        confidence_threshold: Number(s.confidence_threshold),
        sbert_threshold: Number(s.sbert_threshold),
        fusion_weight: Number(s.fusion_weight),
        contact_office: s.contact_office,
        contact_phone: s.contact_phone,
        contact_email: s.contact_email,
        contact_hours: s.contact_hours,
      };
      setS(await api.saveSettings(body));
      toast("Settings saved — applied to the chatbot immediately");
    } catch (err) {
      toast(errorMessage(err), "error");
    }
  }

  async function changePassword(e) {
    e.preventDefault();
    setPwError("");
    if (pw.next !== pw.confirm) return setPwError("The new passwords do not match.");
    try {
      await api.changePassword(pw.current, pw.next);
      setPw({ current: "", next: "", confirm: "" });
      toast("Password changed");
    } catch (err) {
      setPwError(errorMessage(err));
    }
  }

  if (!s) return <p className="muted">Loading settings…</p>;
  const set = (k) => (v) => setS({ ...s, [k]: typeof v === "object" ? v.target.value : v });

  return (
    <div className="grid-2">
      <form className="card form" onSubmit={save}>
        <div className="card-head">
          <h2>Matching thresholds</h2>
        </div>
        <Threshold
          label="TF-IDF confidence threshold"
          help="Queries whose TF-IDF cosine similarity reaches this value are answered directly (default 0.75)."
          value={s.confidence_threshold}
          onChange={set("confidence_threshold")}
        />
        <Threshold
          label="SBERT-stage threshold"
          help="Below the TF-IDF threshold, the semantic (SBERT) score must reach this value, otherwise the fallback message is shown. Higher = fewer wrong answers but more fallbacks."
          value={s.sbert_threshold}
          onChange={set("sbert_threshold")}
        />
        <Threshold
          label="TF-IDF weight in the SBERT stage"
          help="How much keyword (TF-IDF) evidence is combined with the semantic score (0 = SBERT only)."
          value={s.fusion_weight}
          onChange={set("fusion_weight")}
        />
        <div className="card-head">
          <h2>Fallback contact details</h2>
        </div>
        <p className="muted small">Shown to students when no FAQ matches (FR-05).</p>
        <label>
          Office name
          <input value={s.contact_office} onChange={set("contact_office")} />
        </label>
        <label>
          Phone
          <input value={s.contact_phone} onChange={set("contact_phone")} />
        </label>
        <label>
          Email
          <input type="email" value={s.contact_email} onChange={set("contact_email")} />
        </label>
        <label>
          Office hours
          <input value={s.contact_hours} onChange={set("contact_hours")} />
        </label>
        <div className="form-actions">
          <button className="btn primary">Save settings</button>
        </div>
      </form>

      <form className="card form" onSubmit={changePassword}>
        <div className="card-head">
          <h2>Change password</h2>
        </div>
        <p className="muted small">At least 8 characters, including letters and digits. Passwords are stored as bcrypt hashes.</p>
        {pwError && <div className="alert error">{pwError}</div>}
        <label>
          Current password
          <input type="password" value={pw.current} onChange={(e) => setPw({ ...pw, current: e.target.value })} required autoComplete="current-password" />
        </label>
        <label>
          New password
          <input type="password" value={pw.next} onChange={(e) => setPw({ ...pw, next: e.target.value })} required minLength={8} autoComplete="new-password" />
        </label>
        <label>
          Confirm new password
          <input type="password" value={pw.confirm} onChange={(e) => setPw({ ...pw, confirm: e.target.value })} required autoComplete="new-password" />
        </label>
        <div className="form-actions">
          <button className="btn primary">Change password</button>
        </div>
      </form>
    </div>
  );
}

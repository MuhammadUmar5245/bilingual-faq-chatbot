import { createContext, useCallback, useContext, useEffect, useState } from "react";

/* ------------------------------------------------------------- toasts */
const ToastCtx = createContext(() => {});
export const useToast = () => useContext(ToastCtx);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const push = useCallback((text, kind = "ok") => {
    const id = Math.random();
    setToasts((t) => [...t, { id, text, kind }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3500);
  }, []);
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="toasts" role="status">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.kind}`}>
            {t.text}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

/* ------------------------------------------------------------- modal */
export function Modal({ title, onClose, children, wide }) {
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`modal ${wide ? "wide" : ""}`} role="dialog" aria-modal="true" aria-label={title}>
        <div className="modal-head">
          <h2>{title}</h2>
          <button className="btn ghost" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
}

export function Confirm({ title, message, confirmLabel = "Confirm", danger, onConfirm, onClose }) {
  return (
    <Modal title={title} onClose={onClose}>
      <p>{message}</p>
      <div className="form-actions">
        <button className="btn" onClick={onClose}>
          Cancel
        </button>
        <button className={`btn ${danger ? "danger" : "primary"}`} onClick={onConfirm}>
          {confirmLabel}
        </button>
      </div>
    </Modal>
  );
}

/* ------------------------------------------------------------- pagination */
export function Pagination({ page, pages, total, onPage }) {
  return (
    <div className="pagination">
      <span className="muted">
        {total} record{total === 1 ? "" : "s"} · page {page} of {pages}
      </span>
      <div>
        <button className="btn small" disabled={page <= 1} onClick={() => onPage(page - 1)}>
          ‹ Prev
        </button>
        <button className="btn small" disabled={page >= pages} onClick={() => onPage(page + 1)}>
          Next ›
        </button>
      </div>
    </div>
  );
}

export const MethodBadge = ({ method }) => <span className={`badge m-${method}`}>{method}</span>;

export const fmtDate = (iso) =>
  iso ? new Date(iso.endsWith("Z") ? iso : `${iso}Z`).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }) : "–";

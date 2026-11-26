import { useEffect, useMemo, useRef, useState } from "react";
import { createApi } from "./api.js";
import { STRINGS } from "./i18n.js";

const STORE_KEY = "cfaq_widget_v1";
const HISTORY_SIZE = 5; // FR-10: last five query-response pairs

function loadState() {
  try {
    return JSON.parse(sessionStorage.getItem(STORE_KEY)) || {};
  } catch {
    return {};
  }
}

function saveState(state) {
  try {
    sessionStorage.setItem(STORE_KEY, JSON.stringify(state));
  } catch {
    /* storage unavailable (private mode) - the widget still works without it */
  }
}

const newSessionId = () =>
  (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`).replace(/-/g, "");

const ARABIC = /[؀-ۿ]/;

/* ----------------------------------------------------------------- icons */
const Icon = {
  chat: (
    <svg viewBox="0 0 24 24" width="26" height="26" aria-hidden="true">
      <path fill="currentColor" d="M4 4h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H8l-4 4V6a2 2 0 0 1 2-2Zm3 6h10V8H7v2Zm0 4h7v-2H7v2Z" />
    </svg>
  ),
  close: (
    <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
      <path fill="currentColor" d="M6.4 5 5 6.4 10.6 12 5 17.6 6.4 19l5.6-5.6 5.6 5.6 1.4-1.4-5.6-5.6L19 6.4 17.6 5 12 10.6z" />
    </svg>
  ),
  send: (
    <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
      <path fill="currentColor" d="M3 20.5 21 12 3 3.5 3 10l12 2-12 2z" />
    </svg>
  ),
  trash: (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path fill="currentColor" d="M9 3h6l1 2h4v2H4V5h4l1-2Zm-3 6h12l-1 12H7L6 9Z" />
    </svg>
  ),
  history: (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path fill="currentColor" d="M13 3a9 9 0 0 0-9 9H1l3.9 3.9L8.8 12H6a7 7 0 1 1 2.05 4.95l-1.42 1.42A9 9 0 1 0 13 3Zm-1 5v5l4.25 2.52.77-1.28-3.52-2.09V8H12Z" />
    </svg>
  ),
  up: (
    <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
      <path fill="currentColor" d="M2 21h4V9H2v12Zm20-11a2 2 0 0 0-2-2h-6.3l1-4.6v-.3c0-.4-.2-.8-.4-1.1L13.2 1 6.6 7.6c-.4.4-.6.9-.6 1.4V19a2 2 0 0 0 2 2h9a2 2 0 0 0 1.8-1.2l3-7.1c.1-.2.2-.5.2-.7v-2Z" />
    </svg>
  ),
  down: (
    <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
      <path fill="currentColor" d="M22 3h-4v12h4V3ZM2 14a2 2 0 0 0 2 2h6.3l-1 4.6v.3c0 .4.2.8.4 1.1l1.1 1L17.4 16.4c.4-.4.6-.9.6-1.4V5a2 2 0 0 0-2-2H7a2 2 0 0 0-1.8 1.2l-3 7.1c-.1.2-.2.5-.2.7v2Z" />
    </svg>
  ),
  phone: (
    <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
      <path fill="currentColor" d="M6.6 10.8a15 15 0 0 0 6.6 6.6l2.2-2.2c.3-.3.7-.4 1-.2 1.1.4 2.3.6 3.6.6.6 0 1 .4 1 1V20c0 .6-.4 1-1 1A17 17 0 0 1 3 4c0-.6.4-1 1-1h3.5c.6 0 1 .4 1 1 0 1.3.2 2.5.6 3.6.1.3 0 .7-.2 1l-2.3 2.2Z" />
    </svg>
  ),
  mail: (
    <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
      <path fill="currentColor" d="M20 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2Zm0 4-8 5-8-5V6l8 5 8-5v2Z" />
    </svg>
  ),
  clock: (
    <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
      <path fill="currentColor" d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm1 10.4 3.5 2.1-.8 1.3L11 13V7h2v5.4Z" />
    </svg>
  ),
};

/* ----------------------------------------------------------------- pieces */
function TypingIndicator({ t }) {
  return (
    <div className="msg bot" aria-live="polite" aria-label="…">
      <div className="bubble typing">
        <span />
        <span />
        <span />
      </div>
    </div>
  );
}

function ContactCard({ contact, t }) {
  if (!contact) return null;
  return (
    <div className="contact-card">
      <div className="contact-title">{t.contactTitle} — {contact.office}</div>
      <a href={`tel:${contact.phone.replace(/\s/g, "")}`}>
        {Icon.phone} <span>{t.phone}:</span> <bdi>{contact.phone}</bdi>
      </a>
      <a href={`mailto:${contact.email}`}>
        {Icon.mail} <span>{t.email}:</span> <bdi>{contact.email}</bdi>
      </a>
      <div>
        {Icon.clock} <span>{t.hours}:</span> <bdi>{contact.hours}</bdi>
      </div>
    </div>
  );
}

function BotAnswer({ m, t, lang, onAsk, onFeedback, feedback }) {
  const d = m.data;
  const cat = lang === "ar" ? d.category_ar || d.category : d.category;
  return (
    <div className={`msg bot ${d.fallback ? "fallback" : ""}`}>
      <div className="bubble">
        {!d.fallback && d.question && (
          <div className="matched-q" dir="auto">
            {d.question}
          </div>
        )}
        <div className="answer" dir="auto">
          {d.answer}
        </div>
        {d.fallback && <ContactCard contact={d.contact} t={t} />}
        {d.suggestions?.length > 0 && d.fallback && (
          <div className="suggest">
            <div className="suggest-title">{t.didYouMean}</div>
            {d.suggestions.map((s) => (
              <button key={s.id} className="chip small" dir="auto" onClick={() => onAsk(s.question)}>
                {s.question}
              </button>
            ))}
          </div>
        )}
        <div className="meta">
          {cat && !d.fallback && <span className="tag">{cat}</span>}
          {!d.fallback && (
            <span title={`${d.method}`}>
              {t.confidence} {Math.round(d.confidence * 100)}%
            </span>
          )}
          <span>
            {t.detected}: {t.langName[d.lang]}
          </span>
        </div>
        {d.log_id && (
          <div className="feedback">
            {feedback === undefined ? (
              <>
                <span>{t.helpful}</span>
                <button className="icon-btn" aria-label={t.yes} title={t.yes} onClick={() => onFeedback(d.log_id, true)}>
                  {Icon.up}
                </button>
                <button className="icon-btn" aria-label={t.no} title={t.no} onClick={() => onFeedback(d.log_id, false)}>
                  {Icon.down}
                </button>
              </>
            ) : (
              <span className="thanks">{t.thanks}</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/* ----------------------------------------------------------------- widget */
export default function Widget({ apiBase, defaultLang = "en", title, startOpen = false }) {
  const api = useMemo(() => createApi(apiBase), [apiBase]);
  const saved = useMemo(loadState, []);
  const [open, setOpen] = useState(saved.open ?? startOpen);
  const [lang, setLang] = useState(saved.lang || defaultLang);
  const [messages, setMessages] = useState(saved.messages || []);
  const [history, setHistory] = useState(saved.history || []);
  const [feedback, setFeedback] = useState(saved.feedback || {});
  const [sessionId] = useState(saved.sessionId || newSessionId());
  const [view, setView] = useState("chat");
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const [categories, setCategories] = useState([]);
  const [popular, setPopular] = useState([]);
  const listRef = useRef(null);
  const inputRef = useRef(null);
  const t = STRINGS[lang];

  useEffect(() => {
    saveState({ open, lang, messages: messages.slice(-40), history, feedback, sessionId });
  }, [open, lang, messages, history, feedback, sessionId]);

  useEffect(() => {
    if (!open) return;
    api.categories().then(setCategories).catch(() => {});
    api.popular(lang).then(setPopular).catch(() => {});
  }, [open, lang, api]);

  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [messages, typing, open, view]);

  useEffect(() => {
    if (open && view === "chat") inputRef.current?.focus();
  }, [open, view]);

  const push = (m) => setMessages((ms) => [...ms, { id: `${Date.now()}-${Math.random()}`, ...m }]);

  async function ask(text) {
    const q = (text ?? input).trim();
    if (!q || typing) return;
    setInput("");
    setView("chat");
    if (q.length > 500) {
      push({ role: "notice", text: t.tooLong });
      return;
    }
    push({ role: "user", text: q });
    setTyping(true);
    try {
      const data = await api.chat(q, sessionId);
      // Auto language detection (FR-01): follow the language the student writes in.
      if (data.lang && data.lang !== lang) setLang(data.lang);
      push({ role: "bot", data });
      setHistory((h) => [...h, { q, a: data.answer, fallback: data.fallback, lang: data.lang }].slice(-HISTORY_SIZE));
    } catch (err) {
      const status = err?.response?.status;
      const strings = STRINGS[ARABIC.test(q) ? "ar" : lang];
      push({ role: "notice", text: status === 429 ? strings.rateLimited : strings.error });
    } finally {
      setTyping(false);
    }
  }

  async function showCategory(cat) {
    push({ role: "user", text: lang === "ar" ? cat.name_ar : cat.name_en });
    setTyping(true);
    try {
      const qs = await api.popular(lang, cat.id, 8);
      push({ role: "topic", category: cat, questions: qs });
    } catch {
      push({ role: "notice", text: t.error });
    } finally {
      setTyping(false);
    }
  }

  async function sendFeedback(logId, helpful) {
    setFeedback((f) => ({ ...f, [logId]: helpful }));
    try {
      await api.feedback(logId, helpful);
    } catch {
      /* feedback is best-effort */
    }
  }

  function clearChat() {
    setMessages([]);
    setFeedback({});
    setView("chat");
  }

  const dir = lang === "ar" ? "rtl" : "ltr";

  return (
    <div className={`cfaq-root ${open ? "is-open" : ""}`} dir={dir} lang={lang}>
      {open && (
        <section className="panel" role="dialog" aria-label={title || t.title}>
          <header className="head">
            <div className="avatar" aria-hidden="true">
              {Icon.chat}
            </div>
            <div className="titles">
              <div className="title">{title || t.title}</div>
              <div className="subtitle">{t.subtitle}</div>
            </div>
            <div className="head-actions">
              <button className="lang-btn" onClick={() => setLang(lang === "en" ? "ar" : "en")} aria-label={t.toggleLabel}>
                {t.toggle}
              </button>
              <button
                className={`icon-btn light ${view === "history" ? "active" : ""}`}
                onClick={() => setView(view === "history" ? "chat" : "history")}
                aria-label={t.history}
                title={t.history}
              >
                {Icon.history}
              </button>
              <button className="icon-btn light" onClick={clearChat} aria-label={t.clear} title={t.clear}>
                {Icon.trash}
              </button>
              <button className="icon-btn light" onClick={() => setOpen(false)} aria-label={t.close} title={t.close}>
                {Icon.close}
              </button>
            </div>
          </header>

          {view === "history" ? (
            <div className="body history-view">
              <div className="history-head">
                <strong>{t.history}</strong>
                <span>{t.historyNote}</span>
              </div>
              {history.length === 0 && <p className="muted">{t.historyEmpty}</p>}
              <ol className="history-list">
                {[...history].reverse().map((h, i) => (
                  <li key={i} className={h.fallback ? "fallback" : ""}>
                    <button className="history-q" dir="auto" onClick={() => ask(h.q)}>
                      {h.q}
                    </button>
                    <div className="history-a" dir="auto">
                      {h.a}
                    </div>
                  </li>
                ))}
              </ol>
              <button className="link-btn" onClick={() => setView("chat")}>
                {t.back}
              </button>
            </div>
          ) : (
            <div className="body" ref={listRef} aria-live="polite">
              <div className="msg bot">
                <div className="bubble">{t.greeting}</div>
              </div>
              {/* Table 19: students are asked not to enter personal details */}
              <p className="privacy-note">{t.privacy}</p>
              {messages.length === 0 && popular.length > 0 && (
                <div className="welcome-block">
                  <div className="section-title">{t.popular}</div>
                  <div className="chips column">
                    {popular.map((p) => (
                      <button key={p.id} className="chip" dir="auto" onClick={() => ask(p.question)}>
                        {p.question}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {messages.map((m) => {
                if (m.role === "user")
                  return (
                    <div key={m.id} className="msg user">
                      <div className="bubble" dir="auto">
                        {m.text}
                      </div>
                    </div>
                  );
                if (m.role === "notice")
                  return (
                    <div key={m.id} className="msg bot">
                      <div className="bubble notice">{m.text}</div>
                    </div>
                  );
                if (m.role === "topic")
                  return (
                    <div key={m.id} className="msg bot">
                      <div className="bubble">
                        <div className="chips column">
                          {m.questions.map((q) => (
                            <button key={q.id} className="chip" dir="auto" onClick={() => ask(q.question)}>
                              {q.question}
                            </button>
                          ))}
                        </div>
                      </div>
                    </div>
                  );
                return (
                  <BotAnswer
                    key={m.id}
                    m={m}
                    t={t}
                    lang={lang}
                    onAsk={ask}
                    onFeedback={sendFeedback}
                    feedback={feedback[m.data.log_id]}
                  />
                );
              })}
              {typing && <TypingIndicator t={t} />}
            </div>
          )}

          {view === "chat" && categories.length > 0 && (
            <nav className="chips-bar" aria-label={t.categories}>
              {categories.map((c) => (
                <button key={c.id} className="chip outline" onClick={() => showCategory(c)}>
                  {lang === "ar" ? c.name_ar : c.name_en}
                </button>
              ))}
            </nav>
          )}

          <form
            className="composer"
            onSubmit={(e) => {
              e.preventDefault();
              ask();
            }}
          >
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={t.placeholder}
              aria-label={t.placeholder}
              dir="auto"
              maxLength={500}
            />
            <button type="submit" className="send-btn" disabled={!input.trim() || typing} aria-label={t.send}>
              {Icon.send}
            </button>
          </form>
          <div className="foot">{t.poweredBy}</div>
        </section>
      )}
      <button className="launcher" onClick={() => setOpen(!open)} aria-label={open ? t.close : t.open} aria-expanded={open}>
        {open ? Icon.close : Icon.chat}
      </button>
    </div>
  );
}

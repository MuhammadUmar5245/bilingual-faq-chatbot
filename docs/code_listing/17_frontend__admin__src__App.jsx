import { useCallback, useEffect, useState } from "react";
import { api, setUnauthorizedHandler } from "./api.js";
import { ToastProvider } from "./components/ui.jsx";
import Login from "./pages/Login.jsx";
import Overview from "./pages/Overview.jsx";
import Faqs from "./pages/Faqs.jsx";
import Logs from "./pages/Logs.jsx";
import Unanswered from "./pages/Unanswered.jsx";
import Settings from "./pages/Settings.jsx";

const PAGES = [
  { id: "overview", label: "Overview", icon: "M3 13h8V3H3v10Zm0 8h8v-6H3v6Zm10 0h8V11h-8v10Zm0-18v6h8V3h-8Z", el: Overview },
  { id: "faqs", label: "FAQ Management", icon: "M4 4h16v2H4V4Zm0 5h16v2H4V9Zm0 5h10v2H4v-2Zm0 5h10v2H4v-2Z", el: Faqs },
  { id: "logs", label: "Conversation Logs", icon: "M4 4h16v12H5.2L4 17.2V4Zm2 3v2h12V7H6Zm0 4v2h8v-2H6Z", el: Logs },
  { id: "unanswered", label: "Unanswered Queries", icon: "M11 15h2v2h-2v-2Zm0-8h2v6h-2V7Zm1-5a10 10 0 1 0 0 20 10 10 0 0 0 0-20Z", el: Unanswered },
  { id: "settings", label: "Settings", icon: "M19.4 13a7.5 7.5 0 0 0 0-2l2.1-1.6-2-3.5-2.5 1a7 7 0 0 0-1.7-1L15 3h-4l-.4 2.7a7 7 0 0 0-1.7 1l-2.5-1-2 3.5L6.6 11a7.5 7.5 0 0 0 0 2l-2.1 1.6 2 3.5 2.5-1c.5.4 1.1.7 1.7 1L11 21h4l.4-2.7c.6-.3 1.2-.6 1.7-1l2.5 1 2-3.5-2.2-1.8ZM13 15.5a3.5 3.5 0 1 1 0-7 3.5 3.5 0 0 1 0 7Z", el: Settings },
];

function useHashRoute() {
  const read = () => {
    const [page, query] = window.location.hash.replace(/^#\/?/, "").split("?");
    return { page: page || "overview", params: Object.fromEntries(new URLSearchParams(query || "")) };
  };
  const [route, setRoute] = useState(read);
  useEffect(() => {
    const onHash = () => setRoute(read());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  const navigate = useCallback((page, params) => {
    const q = params ? `?${new URLSearchParams(params)}` : "";
    window.location.hash = `#/${page}${q}`;
  }, []);
  return [route, navigate];
}

export default function App() {
  const [user, setUser] = useState(undefined); // undefined = checking session
  const [route, navigate] = useHashRoute();
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    setUnauthorizedHandler(() => setUser(null));
    api.me().then((r) => setUser(r.user)).catch(() => setUser(null));
  }, []);

  if (user === undefined) return <div className="splash">Loading…</div>;

  if (!user)
    return (
      <ToastProvider>
        <Login onLogin={setUser} />
      </ToastProvider>
    );

  const current = PAGES.find((p) => p.id === route.page) || PAGES[0];
  const Page = current.el;

  async function logout() {
    try {
      await api.logout();
    } finally {
      setUser(null);
    }
  }

  return (
    <ToastProvider>
      <div className={`layout ${menuOpen ? "menu-open" : ""}`}>
        <aside className="sidebar">
          <div className="brand">
            <div className="brand-mark">FAQ</div>
            <div>
              <div className="brand-title">College FAQ Chatbot</div>
              <div className="brand-sub">Admin dashboard</div>
            </div>
          </div>
          <nav>
            {PAGES.map((p) => (
              <a
                key={p.id}
                href={`#/${p.id}`}
                className={p.id === current.id ? "active" : ""}
                onClick={() => setMenuOpen(false)}
              >
                <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
                  <path fill="currentColor" d={p.icon} />
                </svg>
                {p.label}
              </a>
            ))}
          </nav>
          <div className="sidebar-foot">
            <div className="user">
              Signed in as <strong>{user.username}</strong>
            </div>
            <button className="btn ghost light" onClick={logout}>
              Log out
            </button>
          </div>
        </aside>
        <div className="main">
          <header className="topbar">
            <button className="btn ghost menu-btn" onClick={() => setMenuOpen(!menuOpen)} aria-label="Menu">
              ☰
            </button>
            <h1>{current.label}</h1>
            <a className="btn ghost" href="/" target="_blank" rel="noreferrer">
              Open chatbot ↗
            </a>
          </header>
          <div className="content">
            <Page params={route.params} navigate={navigate} user={user} />
          </div>
        </div>
      </div>
    </ToastProvider>
  );
}

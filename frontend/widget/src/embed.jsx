/*
 * Embeddable entry point (FR-08). A college website adds the chatbot with one tag:
 *
 *   <script src="https://chatbot.example.edu.om/widget.js"
 *           data-api="https://chatbot.example.edu.om"   (optional - defaults to the script's origin)
 *           data-lang="en"                               (optional - en | ar)
 *           data-title="Gulf College Assistant"          (optional)
 *           data-open="false" defer></script>
 *
 * The widget renders inside a Shadow DOM so its styles are isolated from the host page.
 */
import { createRoot } from "react-dom/client";
import Widget from "./Widget.jsx";
import css from "./styles.css?inline";

// Captured while the script executes; document.currentScript is null inside later callbacks.
const SCRIPT = document.currentScript || document.querySelector('script[src*="widget.js"]');
const currentScript = () => SCRIPT;

function mount(options = {}) {
  const script = currentScript();
  const scriptOrigin = script?.src ? new URL(script.src, window.location.href).origin : window.location.origin;
  const cfg = {
    apiBase: options.api || script?.dataset.api || scriptOrigin,
    defaultLang: options.lang || script?.dataset.lang || (document.documentElement.lang === "ar" ? "ar" : "en"),
    title: options.title || script?.dataset.title,
    startOpen: (options.open ?? script?.dataset.open) === true || script?.dataset.open === "true",
  };
  const host = document.createElement("div");
  host.id = "college-faq-widget";
  document.body.appendChild(host);
  const shadow = host.attachShadow({ mode: "open" });
  const style = document.createElement("style");
  style.textContent = css;
  shadow.appendChild(style);
  const container = document.createElement("div");
  shadow.appendChild(container);
  createRoot(container).render(<Widget {...cfg} />);
  return host;
}

if (!SCRIPT || SCRIPT.dataset.autoMount !== "false") {
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => mount());
  else mount();
}

export { mount };

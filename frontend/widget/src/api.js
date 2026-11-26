import axios from "axios";

export function createApi(baseUrl) {
  const http = axios.create({ baseURL: `${baseUrl.replace(/\/$/, "")}/api`, timeout: 15000 });
  return {
    chat: (message, sessionId) => http.post("/chat", { message, session_id: sessionId }).then((r) => r.data),
    feedback: (logId, helpful) => http.post("/feedback", { log_id: logId, helpful }).then((r) => r.data),
    categories: () => http.get("/categories").then((r) => r.data),
    popular: (lang, categoryId, limit = 6) =>
      http
        .get("/faqs/popular", { params: { lang, limit, ...(categoryId ? { category_id: categoryId } : {}) } })
        .then((r) => r.data),
  };
}

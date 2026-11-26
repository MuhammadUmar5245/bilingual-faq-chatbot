import axios from "axios";

// Same-origin requests (Nginx proxies /api to Flask), so the session cookie is sent automatically.
const http = axios.create({ baseURL: "/api", withCredentials: true, timeout: 20000 });

let onUnauthorized = () => {};
export const setUnauthorizedHandler = (fn) => (onUnauthorized = fn);

http.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err?.response?.status === 401 && !err.config.url.endsWith("/admin/login")) onUnauthorized();
    return Promise.reject(err);
  }
);

export const errorMessage = (err) => err?.response?.data?.error || err?.message || "Request failed";

const data = (p) => p.then((r) => r.data);

export const api = {
  login: (username, password) => data(http.post("/admin/login", { username, password })),
  logout: () => data(http.post("/admin/logout")),
  me: () => data(http.get("/admin/me")),
  stats: (days = 14) => data(http.get("/admin/stats", { params: { days } })),
  categories: () => data(http.get("/admin/categories")),
  faqs: (params) => data(http.get("/admin/faqs", { params })),
  createFaq: (body) => data(http.post("/admin/faqs", body)),
  updateFaq: (id, body) => data(http.put(`/admin/faqs/${id}`, body)),
  toggleFaq: (id) => data(http.patch(`/admin/faqs/${id}/toggle`)),
  deleteFaq: (id) => data(http.delete(`/admin/faqs/${id}`)),
  importFaqs: (file, mode) => {
    const form = new FormData();
    form.append("file", file);
    form.append("mode", mode);
    return data(http.post("/admin/faqs/import", form));
  },
  exportUrl: "/api/admin/faqs/export",
  logs: (params) => data(http.get("/admin/logs", { params })),
  unanswered: (params) => data(http.get("/admin/unanswered", { params })),
  settings: () => data(http.get("/admin/settings")),
  saveSettings: (body) => data(http.put("/admin/settings", body)),
  changePassword: (current_password, new_password) =>
    data(http.put("/admin/password", { current_password, new_password })),
  health: () => data(http.get("/health")),
};

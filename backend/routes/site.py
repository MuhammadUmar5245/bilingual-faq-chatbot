"""Optional static hosting of the built frontends for local runs without Docker.

In the Docker deployment Nginx serves these files; this blueprint is only registered when the
`frontend/*/dist` folders exist and SERVE_FRONTEND=1 (the default for local development).
  /            -> docs/demo-college-site.html (a college page embedding the widget, FR-08)
  /widget.js   -> frontend/widget/dist/widget.js
  /admin/...   -> frontend/admin/dist (single-page app)
"""
from flask import Blueprint, Response, abort, send_from_directory

from app.config import PROJECT_DIR

WIDGET_DIST = PROJECT_DIR / "frontend" / "widget" / "dist"
ADMIN_DIST = PROJECT_DIR / "frontend" / "admin" / "dist"
DEMO_PAGE = PROJECT_DIR / "docs" / "demo-college-site.html"

site_bp = Blueprint("site", __name__)


@site_bp.get("/")
def demo_site():
    if not DEMO_PAGE.exists():
        abort(404)
    html = DEMO_PAGE.read_text(encoding="utf-8").replace("http://localhost:8088/widget.js", "/widget.js")
    return Response(html, mimetype="text/html")


@site_bp.get("/widget.js")
def widget_js():
    return send_from_directory(WIDGET_DIST, "widget.js", mimetype="application/javascript", max_age=300)


@site_bp.get("/admin/")
@site_bp.get("/admin/<path:path>")
def admin_app(path="index.html"):
    target = ADMIN_DIST / path
    if path != "index.html" and target.is_file():
        return send_from_directory(ADMIN_DIST, path)
    return send_from_directory(ADMIN_DIST, "index.html")


def frontend_available() -> bool:
    return (WIDGET_DIST / "widget.js").exists() and (ADMIN_DIST / "index.html").exists()

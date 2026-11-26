"""Integration tests - local static hosting of the demo site, widget.js and admin app (FR-08)."""
import pytest

from routes.site import frontend_available
from tests.conftest import make_app

pytestmark = pytest.mark.skipif(not frontend_available(), reason="frontend not built (npm run build)")


@pytest.fixture()
def site():
    return make_app(SERVE_FRONTEND=True).test_client()


def test_demo_site_embeds_widget_with_one_script_tag(site):
    html = site.get("/").data.decode()
    assert html.count('<script src="/widget.js"') == 1


def test_widget_js_served(site):
    r = site.get("/widget.js")
    assert r.status_code == 200 and "javascript" in r.content_type and len(r.data) > 10000


def test_admin_spa_and_fallback(site):
    assert b'<div id="root">' in site.get("/admin/").data
    assert b'<div id="root">' in site.get("/admin/faqs/anything").data

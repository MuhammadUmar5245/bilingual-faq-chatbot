"""Capture screenshots of every function for Chapter 5.1.2 (Playwright).

Run against a FRESH Docker deployment (so statistics only reflect this demonstration session):
    docker compose down -v && CHAT_RATE_LIMIT="1000 per minute" docker compose up -d
    python screenshots/capture_screenshots.py --base http://localhost:8088

Step 1 sends a short demonstration session of real queries through the public API (they are
processed and logged by the system like any other query), so the dashboard has data to show.
Step 2 captures the student widget and the admin dashboard. Changes made for the screenshots
(test FAQ, disabled FAQ, imported rows) are undone at the end.
"""
import argparse
import time
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
W = "#college-faq-widget >> css="
ADMIN = ("admin", "Admin@12345")

DEMO_SESSION = [  # (session, query, feedback)
    ("demo-1", "What are the admission requirements for a bachelor's degree?", True),
    ("demo-1", "can i skip the foundation year if i have ielts 6", True),
    ("demo-1", "how much does the hostel cost", True),
    ("demo-2", "كم تبلغ الرسوم الدراسية؟", True),
    ("demo-2", "متى تبدأ الامتحانات النهائية", True),
    ("demo-2", "هل يوجد سكن للطالبات", None),
    ("demo-3", "how do i drop a course", True),
    ("demo-3", "what is the attendance policy", False),
    ("demo-3", "is there free wifi on campus", True),
    ("demo-4", "can I pay fees in instalments", True),
    ("demo-4", "what happens if I fail a course twice", None),
    ("demo-4", "do you have a cyber security degree", True),
    ("demo-5", "is there a swimming pool", None),
    ("demo-5", "what is the weather in muscat", None),
    ("demo-5", "how do I apply for a MoHERI scholarship", True),
    ("demo-6", "كيف أتقدم بطلب الالتحاق بالكلية", True),
    ("demo-6", "أين أجد جدول امتحاناتي", True),
    ("demo-6", "هل يمكنني ركن سيارتي في الكلية", None),
    ("demo-7", "when are exam results released", True),
    ("demo-7", "can my company sponsor my studies", None),
    ("demo-7", "who won the football match", None),
    ("demo-8", "how do I get my transcript", True),
    ("demo-8", "is there a bus from seeb", True),
    ("demo-8", "how to reset my portal password", False),
    ("demo-9", "what is a resit exam", True),
    ("demo-9", "what bachelor programmes do you offer", True),
    ("demo-9", "do you have a gym", None),
]


def seed_demo_session(base):
    api = f"{base}/api"
    for sid, q, fb in DEMO_SESSION:
        r = requests.post(f"{api}/chat", json={"message": q, "session_id": sid}, timeout=30).json()
        if fb is not None and r.get("log_id"):
            requests.post(f"{api}/feedback", json={"log_id": r["log_id"], "helpful": fb}, timeout=10)


def shot(page, name, full=False, keep_toasts=False):
    page.wait_for_timeout(350)
    if not keep_toasts:  # hide notifications left over from earlier steps
        page.evaluate("document.querySelectorAll('.toast').forEach(t => t.style.visibility = 'hidden')")
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=full)
    print("saved", name)


def widget(page, base, lang_reset=True):
    page.goto(f"{base}/", wait_until="networkidle")
    if lang_reset:
        page.evaluate("sessionStorage.clear()")
        page.reload(wait_until="networkidle")


def ask(page, q):
    answers = W + ".msg.bot:not(:has(.typing))"
    n = page.locator(answers).count()
    page.locator(W + ".composer input").fill(q)
    page.locator(W + ".composer input").press("Enter")
    page.locator(answers).nth(n).wait_for(timeout=20000)
    page.locator(W + ".bubble.typing").wait_for(state="detached", timeout=20000)


def capture_widget(browser, base):
    ctx = browser.new_context(viewport={"width": 1366, "height": 800}, device_scale_factor=1.5)
    p = ctx.new_page()
    widget(p, base)
    shot(p, "01_college_site_with_chat_bubble")
    p.locator(W + ".launcher").click()
    p.locator(W + ".welcome-block").wait_for()
    shot(p, "02_chat_welcome_popular_questions")

    ask(p, "can I pay my fees in instalments?")
    shot(p, "03_chat_english_answer")

    # Typing indicator: delay the API response so the indicator is visible
    def slow(route):
        time.sleep(1.5)
        route.continue_()
    p.route("**/api/chat", slow)
    p.locator(W + ".composer input").fill("When are the final exams?")
    p.locator(W + ".composer input").press("Enter")
    p.locator(W + ".bubble.typing").wait_for()
    shot(p, "04_chat_typing_indicator")
    p.locator(W + ".bubble.typing").wait_for(state="detached", timeout=20000)
    p.unroute("**/api/chat")

    ask(p, "كيف أدفع الرسوم الدراسية؟")
    shot(p, "05_chat_arabic_auto_detected_rtl")

    p.locator(W + "button[aria-label='Clear chat'], button[aria-label='مسح المحادثة']").first.click()
    p.locator(W + ".lang-btn").click()  # back to English
    p.locator(W + ".chips-bar .chip").nth(5).click()  # Student Services
    p.locator(W + ".msg.bot .chips.column").last.wait_for()
    shot(p, "06_category_chip_questions")

    ask(p, "what is the capital of france")
    shot(p, "07_fallback_contact_card")

    ask(p, "Is there a dress code?")
    p.locator(W + ".feedback button").last.wait_for()
    p.locator(W + ".feedback").last.locator("button").first.click()
    shot(p, "08_feedback_thumbs_up_thanks")

    for q in ("library opening hours", "is there a cafeteria", "how do I get my student ID card"):
        ask(p, q)
    p.locator(W + "button[aria-label='Recent questions']").click()
    shot(p, "09_history_last_five_questions")
    p.locator(W + "button[aria-label='Recent questions']").click()

    p.locator(W + "button[aria-label='Clear chat']").click()
    p.locator(W + ".lang-btn").click()
    shot(p, "10_arabic_interface_toggle")
    ctx.close()

    # Mobile
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    p = ctx.new_page()
    widget(p, base)
    shot(p, "11_mobile_college_site")
    p.locator(W + ".launcher").click()
    ask(p, "how do I apply to the college?")
    shot(p, "12_mobile_chat_english")
    ask(p, "هل يوجد سكن للطلاب؟")
    shot(p, "13_mobile_chat_arabic")
    ctx.close()


def capture_admin(browser, base):
    api = f"{base}/api"
    s = requests.Session()
    s.post(f"{api}/admin/login", json={"username": ADMIN[0], "password": ADMIN[1]}).raise_for_status()

    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1.5)
    p = ctx.new_page()
    p.on("pageerror", lambda e: print("PAGE ERROR:", e))
    p.goto(f"{base}/admin/", wait_until="networkidle")
    shot(p, "14_admin_login")
    p.fill("input[autocomplete=username]", ADMIN[0])
    p.fill("input[type=password]", "wrong-password")
    p.click("button.primary")
    p.locator(".alert.error").wait_for()
    shot(p, "15_admin_login_failed")
    p.fill("input[type=password]", ADMIN[1])
    p.click("button.primary")
    p.locator(".kpis").wait_for()
    shot(p, "16_admin_overview_dashboard", full=True)

    p.goto(f"{base}/admin/#/faqs")
    p.locator("table.table tbody tr").first.wait_for()
    shot(p, "17_admin_faq_table")
    p.fill("input.search", "hostel")
    p.select_option("select[aria-label=Category]", label="Student Services")
    p.wait_for_timeout(900)
    p.locator("table .link").first.click()
    shot(p, "18_admin_faq_search_filter_preview")

    p.fill("input.search", "")
    p.select_option("select[aria-label=Category]", value="")
    p.click("text=+ Add FAQ")
    p.fill(".modal input >> nth=0", "Is there a swimming pool on campus?")
    p.fill(".modal input >> nth=1", "هل يوجد مسبح في الحرم الجامعي؟")
    p.fill(".modal textarea >> nth=0", "Yes. The indoor swimming pool in the Sports Complex is open from 6:00 am to 9:00 pm for students with a valid ID card.")
    p.fill(".modal textarea >> nth=1", "نعم، المسبح الداخلي في المجمع الرياضي مفتوح من الساعة 6 صباحاً حتى 9 مساءً للطلبة الحاملين لبطاقة جامعية سارية.")
    p.select_option(".modal select", label="Student Services — خدمات الطلبة")
    p.fill(".modal input >> nth=2", "pool, swimming, sports, مسبح, سباحة")
    shot(p, "19_admin_add_faq_form")
    p.click(".modal button.primary")
    p.locator(".toast").wait_for()
    shot(p, "20_admin_faq_saved_index_rebuilt", keep_toasts=True)
    new_id = s.get(f"{api}/admin/faqs", params={"q": "swimming pool"}).json()["items"][0]["id"]

    # The chatbot answers the new FAQ immediately
    wctx = browser.new_context(viewport={"width": 1366, "height": 800}, device_scale_factor=1.5)
    wp = wctx.new_page()
    widget(wp, base)
    wp.locator(W + ".launcher").click()
    ask(wp, "can I go swimming at the college?")
    shot(wp, "21_chatbot_uses_new_faq_immediately")
    wctx.close()

    p.goto(f"{base}/admin/#/faqs")
    p.fill("input.search", "swimming")
    p.wait_for_timeout(900)
    p.locator("tr", has_text="swimming pool").locator("text=Edit").click()
    shot(p, "22_admin_edit_faq")
    p.keyboard.press("Escape")
    p.locator("tr", has_text="swimming pool").locator("text=Disable").click()
    p.locator(".toast").wait_for()
    shot(p, "23_admin_faq_disabled", keep_toasts=True)
    p.locator("tr", has_text="swimming pool").locator("text=Delete").click()
    shot(p, "24_admin_delete_confirmation")
    p.locator(".modal button.danger").click()
    p.locator(".toast").last.wait_for()

    csv_path = OUT / "_import_example.csv"
    csv_path.write_text("question_en,question_ar,answer,answer_ar,category,keywords\n"
                        "Does the college have a bookshop?,هل توجد مكتبة لبيع الكتب في الكلية؟,"
                        "\"Yes, the bookshop in the Student Centre sells textbooks and stationery.\","
                        "\"نعم، تبيع مكتبة مركز الطلبة الكتب والقرطاسية.\",Student Services,\"bookshop, books, مكتبة\"\n"
                        "Row without an answer,,,,Fees,\n", encoding="utf-8")
    p.goto(f"{base}/admin/#/faqs")
    p.click("text=Import CSV")
    p.set_input_files(".modal input[type=file]", str(csv_path))
    p.click(".modal button.primary")
    p.locator(".modal .alert.ok").wait_for()
    shot(p, "25_admin_csv_import_result")
    p.keyboard.press("Escape")
    csv_path.unlink()
    for f in s.get(f"{api}/admin/faqs", params={"q": "bookshop"}).json()["items"]:
        s.delete(f"{api}/admin/faqs/{f['id']}")

    p.goto(f"{base}/admin/#/logs")
    p.locator("table.table tbody tr").first.wait_for()
    shot(p, "26_admin_conversation_logs")
    p.select_option("select[aria-label=Language]", "ar")
    p.wait_for_timeout(800)
    shot(p, "27_admin_logs_filtered_arabic")

    p.goto(f"{base}/admin/#/unanswered")
    try:
        p.locator("table.table tbody tr").first.wait_for(timeout=8000)
    except Exception:
        p.screenshot(path=str(OUT / "_debug_unanswered.png"))
        raise
    shot(p, "28_admin_unanswered_queries")
    p.locator("tr", has_text="do you have a gym").locator("text=Create FAQ from this").first.click()
    p.locator(".modal").wait_for()
    shot(p, "29_admin_create_faq_from_unanswered")
    p.keyboard.press("Escape")

    p.goto(f"{base}/admin/#/settings")
    p.locator(".threshold").first.wait_for()
    shot(p, "30_admin_settings_thresholds_contacts", full=True)
    p.fill("input[autocomplete=current-password]", "Admin@12345")
    p.fill("input[autocomplete=new-password] >> nth=0", "short")
    p.fill("input[autocomplete=new-password] >> nth=1", "short")
    p.evaluate("document.querySelectorAll('input[minlength]').forEach(i => i.removeAttribute('minlength'))")
    p.locator("form", has_text="Change password").locator("button.primary").click()
    p.locator(".alert.error").wait_for()
    shot(p, "31_admin_change_password_validation")

    p.goto(f"{base}/admin/#/overview")
    p.locator(".kpis").wait_for()
    p.locator(".chart svg g").last.hover()
    shot(p, "32_admin_chart_tooltip")
    ctx.close()

    mctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    mp = mctx.new_page()
    mp.goto(f"{base}/admin/", wait_until="networkidle")
    mp.fill("input[autocomplete=username]", ADMIN[0])
    mp.fill("input[type=password]", ADMIN[1])
    mp.click("button.primary")
    mp.locator(".kpis").wait_for()
    shot(mp, "33_admin_mobile_view")
    mctx.close()

    s.delete(f"{api}/admin/faqs/{new_id}") if s.get(f"{api}/admin/faqs/{new_id}").ok else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8088")
    ap.add_argument("--no-seed", action="store_true")
    a = ap.parse_args()
    base = a.base.rstrip("/")
    if not a.no_seed:
        seed_demo_session(base)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        capture_widget(browser, base)
        capture_admin(browser, base)
        browser.close()


if __name__ == "__main__":
    main()

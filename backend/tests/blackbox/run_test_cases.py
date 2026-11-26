"""Black-box system test cases (Chapter 5.2.2).

Runs every test case against a RUNNING system (Docker: http://localhost:8088, or local Flask:
http://localhost:5000) through its public interfaces only - the REST API and the browser UI
(Playwright). Actual results are recorded as observed and written to:
    docs/test_cases.md   and   docs/test_cases.xlsx

Usage (from backend/):  python -m tests.blackbox.run_test_cases --base http://localhost:8088
The rate-limit test case runs last because it deliberately exhausts the chat rate limit.
"""
import argparse
import csv
import io
import json
import platform
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import requests

PROJECT = Path(__file__).resolve().parents[3]
DOCS = PROJECT / "docs"
ADMIN = ("admin", "Admin@12345")


@dataclass
class TC:
    id: str
    req: str
    description: str
    preconditions: str
    steps: str
    data: str
    expected: str
    run: callable = None
    actual: str = ""
    status: str = "Not run"
    extra: dict = field(default_factory=dict)


class System:
    def __init__(self, base):
        self.base = base.rstrip("/")
        self.api = f"{self.base}/api"
        self.public = requests.Session()
        self.admin = requests.Session()

    def chat(self, message, session_id="blackbox"):
        t0 = time.perf_counter()
        r = self.public.post(f"{self.api}/chat", json={"message": message, "session_id": session_id}, timeout=30)
        return r, (time.perf_counter() - t0) * 1000

    def login(self):
        r = self.admin.post(f"{self.api}/admin/login", json={"username": ADMIN[0], "password": ADMIN[1]}, timeout=15)
        r.raise_for_status()


def build_cases(sys_: System, browser):
    S, A = sys_, sys_.admin
    created = {}

    def j(r):
        try:
            return r.json()
        except ValueError:
            return {}

    # ---------------------------------------------------------------- FR-01 language
    def tc01():
        r, _ = S.chat("How much are the tuition fees for bachelor's programmes?")
        d = j(r)
        return f"HTTP {r.status_code}; lang={d.get('lang')}; answer_lang={d.get('answer_lang')}; FAQ #{d.get('faq_id')}", \
            r.ok and d.get("lang") == "en" and d.get("answer_lang") == "en"

    def tc02():
        r, _ = S.chat("كم تبلغ الرسوم الدراسية لبرامج البكالوريوس؟")
        d = j(r)
        return f"lang={d.get('lang')}; answer_lang={d.get('answer_lang')}; answer starts '{(d.get('answer') or '')[:30]}…'", \
            d.get("lang") == "ar" and d.get("answer_lang") == "ar"

    def tc03():
        r, _ = S.chat("ابغى احذف مادة")
        d = j(r)
        return f"lang={d.get('lang')}; matched FAQ #{d.get('faq_id')} '{d.get('question')}'; category={d.get('category')}", \
            d.get("lang") == "ar" and d.get("category") == "Registration" and not d.get("fallback")

    # ---------------------------------------------------------------- FR-02 classification
    def tc04():
        r, _ = S.chat("What is the passing mark for a course?")
        d = j(r)
        return f"category={d.get('category')} / {d.get('category_ar')}", d.get("category") == "Examinations"

    def tc05():
        r, _ = S.chat("can you book me a taxi to the airport")
        d = j(r)
        cats = {"Admissions", "Registration", "Fees", "Academic Programmes", "Examinations", "Student Services"}
        return f"fallback={d.get('fallback')}; category={d.get('category')}", d.get("category") in cats

    # ---------------------------------------------------------------- FR-03 retrieval
    def tc06():
        r, _ = S.chat("What is the General Foundation Programme?")
        d = j(r)
        return f"method={d.get('method')}; confidence={d.get('confidence')}; FAQ #{d.get('faq_id')}", \
            d.get("method") == "tfidf" and d.get("faq_id") == 6 and d.get("confidence", 0) >= 0.75

    def tc07():
        r, _ = S.chat("I want to stay in college accommodation")
        d = j(r)
        return f"method={d.get('method')}; confidence={d.get('confidence')}; matched '{d.get('question')}'", \
            d.get("method") == "sbert" and d.get("category") == "Student Services" and "hostel" in (d.get("question") or "").lower()

    def tc08():
        r, _ = S.chat("wen is the registeration peroid")
        d = j(r)
        return f"method={d.get('method')}; matched '{d.get('question')}'", d.get("faq_id") == 37

    # ---------------------------------------------------------------- FR-04 response time
    def tc09():
        times = [S.chat(q)[1] for q in ("hostel fees", "exam timetable", "كيف أدفع الرسوم", "library hours", "transcript")]
        return f"round-trip times (ms): {', '.join(f'{t:.0f}' for t in times)}; max {max(times):.0f} ms", max(times) < 2000

    # ---------------------------------------------------------------- FR-05 fallback
    def tc10():
        r, _ = S.chat("What is the capital of France?")
        d = j(r)
        c = d.get("contact") or {}
        return f"fallback={d.get('fallback')}; contact phone={c.get('phone')}, email={c.get('email')}", \
            d.get("fallback") is True and bool(c.get("phone")) and bool(c.get("email"))

    def tc11():
        r, _ = S.chat("ما هي عاصمة فرنسا؟")
        d = j(r)
        return f"fallback={d.get('fallback')}; text='{(d.get('answer') or '')[:40]}…'", d.get("fallback") and "عذراً" in d.get("answer", "")

    # ---------------------------------------------------------------- FR-06 FAQ management
    def tc12():
        body = {"question_en": "Is there a swimming pool on campus?", "question_ar": "هل يوجد مسبح في الحرم الجامعي؟",
                "answer": "Yes, the indoor pool is open from 6 am to 9 pm.", "category_id": 6,
                "keywords": "pool, swimming, مسبح"}
        r = A.post(f"{S.api}/admin/faqs", json=body)
        created["id"] = j(r).get("id")
        c, _ = S.chat("Is there a swimming pool on campus?")
        return f"create HTTP {r.status_code} (id {created['id']}); chatbot returned FAQ #{j(c).get('faq_id')}", \
            r.status_code == 201 and j(c).get("faq_id") == created["id"]

    def tc13():
        r = A.put(f"{S.api}/admin/faqs/{created['id']}", json={"answer": "Yes. The indoor pool opens 6 am - 10 pm."})
        c, _ = S.chat("Is there a swimming pool on campus?")
        return f"update HTTP {r.status_code}; chatbot answer '{j(c).get('answer')}'", "10 pm" in (j(c).get("answer") or "")

    def tc14():
        r = A.patch(f"{S.api}/admin/faqs/{created['id']}/toggle")
        c, _ = S.chat("Is there a swimming pool on campus?")
        return f"toggle -> is_active={j(r).get('is_active')}; chatbot returned FAQ #{j(c).get('faq_id')}", \
            j(r).get("is_active") is False and j(c).get("faq_id") != created["id"]

    def tc15():
        r = A.patch(f"{S.api}/admin/faqs/{created['id']}/toggle")
        c, _ = S.chat("Is there a swimming pool on campus?")
        return f"toggle -> is_active={j(r).get('is_active')}; chatbot returned FAQ #{j(c).get('faq_id')}", \
            j(r).get("is_active") is True and j(c).get("faq_id") == created["id"]

    def tc16():
        r = A.delete(f"{S.api}/admin/faqs/{created['id']}")
        g = A.get(f"{S.api}/admin/faqs/{created['id']}")
        return f"delete HTTP {r.status_code}; GET afterwards HTTP {g.status_code}", r.ok and g.status_code == 404

    def tc17():
        r = A.post(f"{S.api}/admin/faqs", json={"question_en": "Incomplete FAQ", "category_id": 1})
        return f"HTTP {r.status_code}; error='{j(r).get('error')}'", r.status_code == 400

    def tc18():
        before = A.get(f"{S.api}/admin/faqs", params={"per_page": 1}).json()["total"]
        text = ("question_en,question_ar,answer,category,keywords\n"
                "Does the college have a bookshop?,هل توجد مكتبة لبيع الكتب؟,\"Yes, in the Student Centre.\",Student Services,books\n"
                "Row with no answer,,,Fees,\n")
        r = A.post(f"{S.api}/admin/faqs/import", files={"file": ("import.csv", text.encode("utf-8"), "text/csv")},
                   data={"mode": "append"})
        after = A.get(f"{S.api}/admin/faqs", params={"per_page": 1}).json()["total"]
        found = A.get(f"{S.api}/admin/faqs", params={"q": "bookshop"}).json()["items"]
        for f in found:  # clean up
            A.delete(f"{S.api}/admin/faqs/{f['id']}")
        d = j(r)
        return f"HTTP {r.status_code}; imported={d.get('imported')}, skipped={d.get('skipped')}; FAQ count {before}->{after}", \
            r.status_code == 201 and d.get("imported") == 1 and d.get("skipped") == 1 and after == before + 1

    def tc19():
        r = A.get(f"{S.api}/admin/faqs/export")
        rows = list(csv.DictReader(io.StringIO(r.content.decode("utf-8-sig"))))
        return f"HTTP {r.status_code}; {r.headers.get('Content-Disposition')}; {len(rows)} rows; columns {list(rows[0])[:4]}…", \
            r.ok and len(rows) >= 200 and "question_ar" in rows[0]

    # ---------------------------------------------------------------- FR-07 logging & feedback
    def tc20():
        sid = f"tc20-{int(time.time())}"
        S.chat("When are exam results released?", session_id=sid)
        logs = A.get(f"{S.api}/admin/logs", params={"q": "When are exam results released?"}).json()["items"]
        log = next((l for l in logs if l["session_id"] == sid), None)
        if not log:
            return "log entry not found", False
        return (f"log #{log['id']}: session={log['session_id']}, lang={log['detected_lang']}, FAQ #{log['matched_faq_id']}, "
                f"confidence={log['confidence']}, method={log['method']}, {log['response_ms']} ms"), \
            all(log.get(k) is not None for k in ("matched_faq_id", "confidence", "method", "session_id"))

    def tc21():
        d = A.get(f"{S.api}/admin/logs", params={"method": "fallback"}).json()
        return f"{d['total']} fallback log(s); all method=fallback: {all(i['method'] == 'fallback' for i in d['items'])}", \
            d["total"] >= 1 and all(i["method"] == "fallback" for i in d["items"])

    def tc22():
        r, _ = S.chat("Is there a dress code?")
        log_id = j(r)["log_id"]
        f = S.public.post(f"{S.api}/feedback", json={"log_id": log_id, "helpful": False})
        un = A.get(f"{S.api}/admin/unanswered", params={"type": "unhelpful", "per_page": 50}).json()["items"]
        return f"feedback HTTP {f.status_code}; log #{log_id} listed as unhelpful: {any(u['id'] == log_id for u in un)}", \
            f.status_code == 201 and any(u["id"] == log_id for u in un)

    def tc23():
        before = A.get(f"{S.api}/admin/stats").json()["total_queries"]
        S.chat("Where can I print documents?")
        s = A.get(f"{S.api}/admin/stats").json()
        return (f"total_queries {before}->{s['total_queries']}; resolution_rate={s['resolution_rate']}; "
                f"avg_confidence={s['avg_confidence']}; avg_response_ms={s['avg_response_ms']}"), s["total_queries"] == before + 1

    # ---------------------------------------------------------------- FR-08 / FR-10 / NF-03 UI (Playwright)
    def page(mobile=False):
        ctx = browser.new_context(viewport={"width": 390, "height": 844} if mobile else {"width": 1280, "height": 800},
                                  is_mobile=mobile, has_touch=mobile)
        pg = ctx.new_page()
        pg.goto(f"{S.base}/", wait_until="networkidle")
        return ctx, pg

    W = "#college-faq-widget >> css="

    def ask(pg, q):
        answers = W + ".msg.bot:not(:has(.typing))"
        n = pg.locator(answers).count()
        pg.locator(W + ".composer input").fill(q)
        pg.locator(W + ".composer input").press("Enter")
        pg.locator(answers).nth(n).wait_for(timeout=15000)
        pg.locator(W + ".bubble.typing").wait_for(state="detached", timeout=15000)

    def tc24():
        ctx, pg = page()
        scripts = pg.locator("script[src*='widget.js']").count()
        pg.locator(W + ".launcher").click()
        visible = pg.locator(W + ".panel").is_visible()
        ctx.close()
        return f"{scripts} widget <script> tag on the host page; chat panel visible after click: {visible}", scripts == 1 and visible

    def tc25():
        r = requests.get(f"{S.base}/widget.js", timeout=15)
        return f"HTTP {r.status_code}; Content-Type {r.headers.get('Content-Type')}; {len(r.content) // 1024} KB", \
            r.ok and "javascript" in r.headers.get("Content-Type", "")

    def tc27():
        ctx, pg = page()
        pg.locator(W + ".launcher").click()
        qs = ["hostel fees", "library hours", "exam timetable", "how to pay fees", "is there wifi", "student id card"]
        for q in qs:
            ask(pg, q)
        pg.locator(W + "button[aria-label='Recent questions']").click()
        items = pg.locator(W + ".history-list li .history-q").all_inner_texts()
        ctx.close()
        return f"history shows {len(items)} item(s), newest first: {items}", items == list(reversed(qs[-5:]))

    def tc28():
        ctx, pg = page()
        pg.locator(W + ".launcher").click()
        pg.locator(W + ".lang-btn").click()
        d = pg.locator(W + ".cfaq-root").get_attribute("dir")
        placeholder = pg.locator(W + ".composer input").get_attribute("placeholder")
        ctx.close()
        return f"root dir='{d}'; input placeholder='{placeholder}'", d == "rtl" and placeholder == "اكتب سؤالك…"

    def tc29():
        ctx, pg = page(mobile=True)
        pg.locator(W + ".launcher").click()
        box = pg.locator(W + ".panel").bounding_box()
        ctx.close()
        return f"panel size {box['width']:.0f}x{box['height']:.0f} on a 390x844 screen", box["width"] >= 389 and box["height"] >= 800

    def tc30():
        ctx, pg = page()
        pg.locator(W + ".launcher").click()
        pg.locator(W + ".chips-bar .chip").nth(2).click()  # Fees
        pg.locator(W + ".msg.bot .chips.column").last.wait_for(timeout=10000)
        n = pg.locator(W + ".msg.bot .chips.column").last.locator("button").count()
        ctx.close()
        return f"'Fees' chip listed {n} questions", n >= 5

    def tc31():
        ctx, pg = page()
        pg.locator(W + ".launcher").click()
        ask(pg, "what is the capital of france")
        card = pg.locator(W + ".contact-card").last.inner_text() if pg.locator(W + ".contact-card").count() else ""
        ctx.close()
        return f"fallback card text: {card.replace(chr(10), ' | ')}", "Phone" in card and "Email" in card

    # ---------------------------------------------------------------- FR-09
    def tc26():
        h = S.public.get(f"{S.api}/health").json()
        return f"active_faqs={h['active_faqs']}", h["active_faqs"] >= 200

    # ---------------------------------------------------------------- NF-05 security
    def tc32():
        anon = requests.Session()
        urls = ["/admin/faqs", "/admin/logs", "/admin/stats", "/admin/settings", "/admin/unanswered", "/admin/faqs/export"]
        codes = [anon.get(f"{S.api}{u}").status_code for u in urls]
        codes.append(anon.post(f"{S.api}/admin/faqs", json={}).status_code)
        return f"status codes without login: {codes}", all(c == 401 for c in codes)

    def tc33():
        r = requests.post(f"{S.api}/admin/login", json={"username": "admin", "password": "wrong-password"})
        return f"HTTP {r.status_code}; error='{j(r).get('error')}'", r.status_code == 401

    def tc34():
        codes = [requests.post(f"{S.api}/admin/login", json={"username": p, "password": p}).status_code
                 for p in ("' OR '1'='1", "admin'--")]
        s = A.get(f"{S.api}/admin/faqs", params={"q": "x' OR 1=1; DROP TABLE faqs; --"})
        total = A.get(f"{S.api}/admin/faqs", params={"per_page": 1}).json()["total"]
        return f"login with injection payloads -> {codes}; injected search HTTP {s.status_code}, {s.json()['total']} results; FAQ table still has {total} rows", \
            all(c == 401 for c in codes) and s.ok and total >= 200

    def tc35():
        r = A.put(f"{S.api}/admin/password", json={"current_password": ADMIN[1], "new_password": "abc"})
        return f"HTTP {r.status_code}; error='{j(r).get('error')}'", r.status_code == 400

    # ---------------------------------------------------------------- NF-06 / NF-02 / NF-04
    def tc36():
        orig = A.get(f"{S.api}/admin/settings").json()
        A.put(f"{S.api}/admin/settings", json={"sbert_threshold": 0.99})
        a, _ = S.chat("I want to stay in college accommodation")
        A.put(f"{S.api}/admin/settings", json={"sbert_threshold": orig["sbert_threshold"]})
        b, _ = S.chat("I want to stay in college accommodation")
        return f"with threshold 0.99 -> method={j(a).get('method')}; restored {orig['sbert_threshold']} -> method={j(b).get('method')}", \
            j(a).get("method") == "fallback" and j(b).get("method") == "sbert"

    def tc37():
        svm = json.loads((DOCS / "results" / "summary.json").read_text(encoding="utf-8"))["svm_held_out"]
        return (f"linear SVM category accuracy on held-out in-scope queries = {svm['correct']}/{svm['n']} = "
                f"{svm['accuracy'] * 100:.1f}% (docs/results/summary.json)"), svm["accuracy"] >= 0.85

    # ---------------------------------------------------------------- near misses (FR-03, FR-05)
    def near_miss(query, ok_questions=()):
        r, _ = S.chat(query)
        d = j(r)
        sug = [x["question_en"] for x in d.get("suggestions") or []]
        shown = "fallback" if d.get("fallback") else f"answer '{d.get('question')}'"
        q_en = None
        if not d.get("fallback"):
            q_en = A.get(f"{S.api}/admin/faqs/{d.get('faq_id')}").json().get("question_en")
        ok = d.get("fallback") is True or q_en in ok_questions
        return (f"method={d.get('method')}; confidence={d.get('confidence')}; {shown}"
                + (f" [{q_en}]" if q_en and q_en != d.get("question") else "")
                + f"; suggestions={sug}"), ok

    def tc40():
        return near_miss("هل يوجد سكن للطلاب؟", ("Does the college provide hostel accommodation?",))

    def tc41():
        return near_miss("Tell me about student life")

    def tc42():
        return near_miss("Can I get a refund for the hostel fees?", ("What is the refund policy if I withdraw?",))

    def tc43():
        return near_miss("what is the weather today")

    def tc38():
        h = S.public.get(f"{S.api}/health")
        return f"HTTP {h.status_code}; {h.json()}", h.ok and h.json()["database"] is True

    def tc39():
        codes = []
        for i in range(70):
            r = requests.post(f"{S.api}/chat", json={"message": "fees", "session_id": "flood"})
            codes.append(r.status_code)
        first429 = codes.index(429) + 1 if 429 in codes else None
        return f"70 rapid requests: {codes.count(200)}×200, {codes.count(429)}×429 (first 429 at request {first429})", 429 in codes

    return [
        TC("TC01", "FR-01", "English query is detected as English and answered in English", "System running; FAQ #71 active",
           "1. Open chat 2. Send the query", "How much are the tuition fees for bachelor's programmes?",
           "lang = en, English answer returned", tc01),
        TC("TC02", "FR-01", "Arabic query is detected as Arabic and answered in Arabic", "System running",
           "1. Send an Arabic query", "كم تبلغ الرسوم الدراسية لبرامج البكالوريوس؟", "lang = ar, Arabic answer returned", tc02),
        TC("TC03", "FR-01", "Colloquial Gulf Arabic query is understood", "System running",
           "1. Send colloquial query", "ابغى احذف مادة", "Arabic detected; Registration FAQ (drop a course) returned", tc03),
        TC("TC04", "FR-02", "Query is classified into the correct category", "System running",
           "1. Send query 2. Read category", "What is the passing mark for a course?", "category = Examinations", tc04),
        TC("TC05", "FR-02", "Unanswered query is still assigned one of the six categories", "System running",
           "1. Send out-of-scope query", "can you book me a taxi to the airport", "category is one of the six", tc05),
        TC("TC06", "FR-03", "Exact FAQ question is answered by the TF-IDF stage", "Threshold 0.75",
           "1. Send exact FAQ question", "What is the General Foundation Programme?",
           "method = tfidf, FAQ #6, confidence ≥ 0.75", tc06),
        TC("TC07", "FR-03", "Paraphrase with different words is answered by the fused (SBERT) stage", "SBERT enabled",
           "1. Send paraphrase", "I want to stay in college accommodation",
           "method = sbert (label of the fused stage), hostel FAQ returned", tc07),
        TC("TC08", "FR-03", "Misspelled query is matched to the right FAQ", "System running",
           "1. Send misspelled query", "wen is the registeration peroid", "FAQ #37 (registration period)", tc08),
        TC("TC09", "FR-04", "Answers are returned within two seconds", "Normal load (single user)",
           "1. Send 5 queries 2. Measure round-trip time", "5 mixed EN/AR queries", "every response < 2000 ms", tc09),
        TC("TC10", "FR-05", "Out-of-scope query shows the fallback with contact details", "System running",
           "1. Send unrelated query", "What is the capital of France?", "fallback = true, phone and email shown", tc10),
        TC("TC11", "FR-05", "Arabic out-of-scope query gets the Arabic fallback message", "System running",
           "1. Send Arabic unrelated query", "ما هي عاصمة فرنسا؟", "Arabic fallback text", tc11),
        TC("TC12", "FR-06", "Staff adds a new FAQ and the chatbot answers it immediately", "Logged in as admin",
           "1. Add FAQ 2. Ask the question in chat", "Swimming pool FAQ (EN+AR)", "HTTP 201; chatbot returns the new FAQ", tc12),
        TC("TC13", "FR-06", "Staff edits an FAQ answer", "TC12 passed", "1. Edit answer 2. Ask again",
           "New answer text '…10 pm'", "chatbot shows the edited answer", tc13),
        TC("TC14", "FR-06", "Staff disables an FAQ; chatbot no longer returns it", "TC12 passed", "1. Toggle 2. Ask again",
           "FAQ from TC12", "is_active = false; FAQ not returned", tc14),
        TC("TC15", "FR-06", "Staff re-enables the FAQ", "TC14 passed", "1. Toggle again 2. Ask again", "FAQ from TC12",
           "is_active = true; FAQ returned again", tc15),
        TC("TC16", "FR-06", "Staff deletes an FAQ", "TC12 passed", "1. Delete 2. Try to open it", "FAQ from TC12",
           "delete OK; GET returns 404", tc16),
        TC("TC17", "FR-06", "Form validation rejects an FAQ without an answer", "Logged in", "1. Submit FAQ without answer",
           "question only", "HTTP 400 with error message", tc17),
        TC("TC18", "FR-06, NF-06", "Bulk import from CSV with one invalid row", "Logged in", "1. Upload CSV (append)",
           "2 rows: 1 valid, 1 missing answer", "1 imported, 1 skipped with error", tc18),
        TC("TC19", "FR-06", "Export all FAQs to CSV", "Logged in", "1. Click Export CSV", "–",
           "CSV download with ≥ 200 rows incl. Arabic columns", tc19),
        TC("TC20", "FR-07", "Every query is logged with FAQ, confidence, method and session", "Logged in",
           "1. Ask a question 2. Open logs", "When are exam results released?", "log entry contains all fields", tc20),
        TC("TC21", "FR-07", "Conversation logs can be filtered by method", "Fallback queries exist",
           "1. Filter logs by method = fallback", "method=fallback", "only fallback entries listed", tc21),
        TC("TC22", "FR-07", "Thumbs-down feedback is stored and listed under Unanswered", "System running",
           "1. Ask 2. Click thumbs down 3. Open Unanswered", "Is there a dress code?", "log listed as 'not helpful'", tc22),
        TC("TC23", "FR-07", "Dashboard statistics update after a new query", "Logged in", "1. Read stats 2. Ask 3. Read stats",
           "Where can I print documents?", "total_queries increases by 1", tc23),
        TC("TC24", "FR-08", "Widget is embedded in an external college page with one script tag", "Demo site served",
           "1. Open demo site 2. Click chat bubble", "docs/demo-college-site.html", "one <script> tag; chat panel opens", tc24),
        TC("TC25", "FR-08", "widget.js is downloadable as JavaScript", "Web server running", "1. GET /widget.js", "–",
           "HTTP 200, JavaScript content type", tc25),
        TC("TC26", "FR-09", "Knowledge base holds at least 200 FAQs", "Seeded database", "1. GET /api/health", "–",
           "active_faqs ≥ 200", tc26),
        TC("TC27", "FR-10", "History shows the last five question–answer pairs", "Fresh browser session",
           "1. Ask 6 questions 2. Open history", "6 questions", "exactly the last 5 questions, newest first", tc27),
        TC("TC28", "NF-03", "Arabic toggle switches the whole widget to RTL", "Chat open", "1. Click 'عربي'", "–",
           "dir = rtl; Arabic placeholder", tc28),
        TC("TC29", "NF-03", "Chat is full-screen on a mobile phone", "Phone viewport 390×844", "1. Open chat on mobile",
           "iPhone-size viewport", "panel fills the screen", tc29),
        TC("TC30", "FR-02, NF-03", "Category chip lists the questions of that category", "Chat open",
           "1. Click the 'Fees' chip", "–", "list of Fees questions shown", tc30),
        TC("TC31", "FR-05", "Fallback card in the UI shows phone and email", "Chat open", "1. Ask unrelated question",
           "what is the capital of france", "contact card with phone and email", tc31),
        TC("TC32", "NF-05", "Admin endpoints cannot be used without logging in", "Not logged in",
           "1. Call admin endpoints without a session", "7 admin endpoints", "all return 401", tc32),
        TC("TC33", "NF-05", "Login with a wrong password is rejected", "–", "1. Log in with wrong password",
           "admin / wrong-password", "HTTP 401", tc33),
        TC("TC34", "NF-05", "SQL injection attempts are harmless", "Logged in", "1. Injection in login 2. Injection in search",
           "' OR '1'='1 ; admin'-- ; DROP TABLE", "login rejected; search returns 0; tables intact", tc34),
        TC("TC35", "NF-05", "Weak new password is rejected", "Logged in", "1. Change password to 'abc'", "abc",
           "HTTP 400 with rule message", tc35),
        TC("TC36", "NF-06, FR-03", "Threshold changed in Settings is applied live without restart", "Logged in",
           "1. Set SBERT threshold 0.99 2. Ask paraphrase 3. Restore 4. Ask again", "I want to stay in college accommodation",
           "fallback at 0.99, answered after restore", tc36),
        TC("TC37", "NF-02", "Linear SVM category (intent) classification accuracy on the held-out test set (six "
           "categories) ≥ 85 %", "evaluate.py has been run", "1. Run python -m nlp.evaluate 2. Read svm_held_out",
           "in-scope held-out queries", "accuracy ≥ 85 % (Table 25)", tc37),
        TC("TC38", "NF-04", "Containerised system reports healthy (API + database)", "docker compose up", "1. GET /api/health",
           "–", "HTTP 200, database = true", tc38),
        TC("TC39", "NF-05", "Chat endpoint is rate-limited against flooding", "Default limit 60/min", "1. Send 70 requests quickly",
           "70 × 'fees'", "some requests rejected with HTTP 429", tc39),
        TC("TC40", "FR-03, FR-05", "General Arabic question about student housing (Figure 14b); a narrower hostel FAQ "
           "also exists", "System running", "1. Send the query", "هل يوجد سكن للطلاب؟",
           "General accommodation FAQ, or no confident answer (fallback with 'Did you mean'); not the narrower FAQ", tc40),
        TC("TC41", "FR-03, FR-05", "General English question on a topic where only narrower FAQs exist", "System running",
           "1. Send the query", "Tell me about student life",
           "No confident answer: fallback with related FAQs as 'Did you mean'", tc41),
        TC("TC42", "FR-03", "Question shares keywords with an FAQ but asks for something different", "System running",
           "1. Send the query", "Can I get a refund for the hostel fees?",
           "Refund FAQ or fallback; the hostel-cost FAQ is not returned as a confident answer", tc42),
        TC("TC43", "FR-03, FR-05", "Out-of-scope query whose fused score lies just above the 0.35 threshold",
           "Fused threshold 0.35", "1. Send the query", "what is the weather today",
           "No confident answer (fallback with suggestions)", tc43),
    ]


def write_reports(cases, base, started):
    passed = sum(c.status == "Pass" for c in cases)
    env = f"{base} · {platform.system()} {platform.release()} · run {started:%Y-%m-%d %H:%M}"
    L = ["# Black-box test cases and results (Chapter 5.2.2)", "",
         "Generated by `python -m tests.blackbox.run_test_cases` — actual results are recorded automatically as observed.", "",
         f"- Environment: {env}",
         f"- Result: **{passed} / {len(cases)} passed**", "",
         "| TC ID | Req. | Description | Preconditions | Steps | Test data | Expected result | Actual result | Status |",
         "|---|---|---|---|---|---|---|---|---|"]
    esc = lambda s: str(s).replace("|", "\\|").replace("\n", " ")
    for c in cases:
        L.append("| " + " | ".join(esc(x) for x in (c.id, c.req, c.description, c.preconditions, c.steps, c.data,
                                                     c.expected, c.actual, f"**{c.status}**")) + " |")
    (DOCS / "test_cases.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    wb = Workbook()
    ws = wb.active
    ws.title = "Test cases"
    head = ["TC ID", "FR/NF ID", "Description", "Preconditions", "Steps", "Test Data", "Expected Result", "Actual Result", "Status"]
    ws.append(head)
    for c in cases:
        ws.append([c.id, c.req, c.description, c.preconditions, c.steps, c.data, c.expected, c.actual, c.status])
    widths = [8, 12, 40, 24, 32, 30, 34, 60, 9]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[chr(64 + i)].width = w
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="0B4F8A")
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
        st = row[8]
        st.fill = PatternFill("solid", fgColor="D9F2E3" if st.value == "Pass" else "F9D6D2")
    ws.freeze_panes = "A2"
    info = wb.create_sheet("Summary")
    info.append(["Environment", env])
    info.append(["Passed", passed])
    info.append(["Total", len(cases)])
    wb.save(DOCS / "test_cases.xlsx")
    return passed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8088")
    args = ap.parse_args()
    started = datetime.now()
    system = System(args.base)
    system.login()
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        cases = build_cases(system, browser)
        order = [c for c in cases if c.id != "TC39"] + [c for c in cases if c.id == "TC39"]
        for c in order:
            try:
                c.actual, ok = c.run()
                c.status = "Pass" if ok else "Fail"
            except Exception as e:  # record the error as the actual result
                c.actual, c.status = f"Error: {type(e).__name__}: {e}", "Fail"
                traceback.print_exc()
            print(f"{c.id} {c.status:4}  {c.actual[:110]}")
        browser.close()
    passed = write_reports(cases, args.base, started)
    print(f"\n{passed}/{len(cases)} passed -> docs/test_cases.md, docs/test_cases.xlsx")


if __name__ == "__main__":
    main()

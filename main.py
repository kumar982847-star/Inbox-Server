from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from playwright.sync_api import sync_playwright, TimeoutError
import time

app = FastAPI()
templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------
# RAW COOKIE STRING → PLAYWRIGHT FORMAT
# ------------------------------------
def parse_raw_cookie(raw_cookie: str):
    cookies = []
    for part in raw_cookie.split(";"):
        if "=" in part:
            name, value = part.strip().split("=", 1)
            cookies.append({
                "name": name,
                "value": value,
                "domain": ".facebook.com",
                "path": "/"
            })
    return cookies


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/send_message/")
def send_message(cookies: str = Form(...), thread_id: str = Form(...),
                 messages: str = Form(...), delay: int = Form(0)):

    try:
        cookies_list = parse_raw_cookie(cookies)
    except Exception as e:
        return HTMLResponse(f"Invalid Cookie Format → {e}", status_code=400)

    try:
        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--disable-notifications",
                ]
            )

            context = browser.new_context()
            context.add_cookies(cookies_list)
            page = context.new_page()

            # -----------------------------
            # OPEN CHAT
            # -----------------------------
            page.goto(f"https://www.facebook.com/messages/t/{thread_id}", timeout=60000)

            # -----------------------------
            # POSSIBLE MESSAGE BOX SELECTORS
            # -----------------------------
            candidates = [
                "div[role='textbox'][contenteditable='true']",
                "div[aria-label='Message'][contenteditable='true']",
                "div[data-lexical-editor='true']",
                "div[contenteditable='true']",
                "textarea",
            ]

            message_box = None

            # FIND WORKING SELECTOR
            for sel in candidates:
                try:
                    page.wait_for_selector(sel, timeout=5000)
                    element = page.query_selector(sel)
                    if element:
                        message_box = sel
                        break
                except TimeoutError:
                    pass

            if not message_box:
                return HTMLResponse(
                    "<b>Error:</b> Message box not found (Maybe E2EE chat).",
                    status_code=500
                )

            # -----------------------------
            # SAFE CLICK (BYPASS OVERLAY)
            # -----------------------------
            def safe_click(selector):
                for _ in range(10):
                    try:
                        page.evaluate("el => el.scrollIntoView()", page.query_selector(selector))
                        page.click(selector, force=True)
                        return True
                    except:
                        time.sleep(0.2)
                return False

            # -----------------------------
            # SEND MESSAGES
            # -----------------------------
            for line in messages.splitlines():
                safe_click(message_box)
                page.fill(message_box, line)
                page.keyboard.press("Enter")
                time.sleep(delay)

            browser.close()
            return HTMLResponse("<b>Messages Sent Successfully!</b>", status_code=200)

    except Exception as e:
        return HTMLResponse(f"<b>INTERNAL ERROR:</b> {e}", status_code=500)

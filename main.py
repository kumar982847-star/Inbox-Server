from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from playwright.sync_api import sync_playwright, TimeoutError as PlayTimeout
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

# -----------------------------
# RAW COOKIE STRING → PLAYWRIGHT FORMAT
# -----------------------------
def parse_raw_cookie(raw_cookie: str):
    cookies = []
    parts = raw_cookie.split(";")
    for part in parts:
        if "=" in part:
            name, value = part.strip().split("=", 1)
            cookies.append({
                "name": name.strip(),
                "value": value.strip(),
                "domain": ".facebook.com",
                "path": "/"
            })
    return cookies


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/send_message/")
def send_message(
    cookies: str = Form(...),
    thread_id: str = Form(...),
    messages: str = Form(...),
    delay: int = Form(0)
):
    try:
        cookies_list = parse_raw_cookie(cookies)
    except Exception as e:
        return HTMLResponse(
            content=f"<b>Error:</b> Invalid cookie format → {str(e)}",
            status_code=400
        )

    try:
        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled"
                ]
            )

            context = browser.new_context()
            context.add_cookies(cookies_list)
            page = context.new_page()

            # Open Messenger Thread
            page.goto(
                f"https://www.facebook.com/messages/t/{thread_id}",
                timeout=60000
            )

            # -----------------------------
            # AUTO-DETECT MESSAGE BOX (E2EE + NON-E2EE)
            # -----------------------------
            selectors = [
                'div[aria-label="Message"][contenteditable="true"]',
                'div[role="textbox"][contenteditable="true"]',
                'div[role="textbox"]',
                'div[contenteditable="true"][data-lexical-editor="true"]',
                'div[data-lexical-editor="true"]',
                'div[aria-label="Type a message…"]',
                'div[aria-label="Type a message"]',
                'div[aria-label="Aa"]',
                'div[contenteditable="true"]',
                'textarea',
            ]

            message_box = None

            for sel in selectors:
                try:
                    page.wait_for_selector(sel, timeout=5000)
                    element = page.query_selector(sel)
                    if element:
                        message_box = sel
                        break
                except:
                    pass

            # Fallback: Deep search for contenteditable element
            if not message_box:
                try:
                    ceds = page.query_selector_all("div[contenteditable='true']")
                    if len(ceds) > 0:
                        message_box = "div[contenteditable='true']"
                except:
                    pass

            if not message_box:
                return HTMLResponse(
                    "<b>Error:</b> Message box not found. Probably E2EE protected chat.",
                    status_code=500
                )

            # -----------------------------
            # SEND MESSAGES LINE-BY-LINE
            # -----------------------------
            for msg in messages.splitlines():
                page.click(message_box)
                page.fill(message_box, msg)
                page.keyboard.press("Enter")
                time.sleep(delay)

            browser.close()

        return HTMLResponse("<b>Messages sent successfully!</b>", status_code=200)

    except Exception as e:
        return HTMLResponse(
            content=f"<b>INTERNAL ERROR:</b> {str(e)}",
            status_code=500
        )

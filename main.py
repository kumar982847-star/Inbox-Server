from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from playwright.sync_api import sync_playwright, TimeoutError as PlayTimeout
import json
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
        cookies_list = json.loads(cookies)
    except Exception as e:
        return HTMLResponse(
            content=f"<b>Error:</b> Invalid cookies JSON → {str(e)}",
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

            page.goto(
                f"https://www.facebook.com/messages/t/{thread_id}",
                timeout=60000
            )

            # ALL POSSIBLE FB / MESSENGER TEXTBOX PATTERNS (E2EE + normal)
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

            # TRY ALL SELECTORS ONE BY ONE
            for sel in selectors:
                try:
                    page.wait_for_selector(sel, timeout=5000)
                    element = page.query_selector(sel)
                    if element:
                        message_box = sel
                        break
                except:
                    pass

            # FAILSAFE: search deepest contenteditable
            if not message_box:
                try:
                    elements = page.query_selector_all("div[contenteditable='true']")
                    if len(elements) > 0:
                        message_box = "div[contenteditable='true']"
                except:
                    pass

            if not message_box:
                return HTMLResponse(
                    "<b>Error:</b> Message box not found. This chat is E2EE or layout changed.",
                    status_code=500
                )

            # SEND MESSAGES
            for msg in messages.splitlines():
                page.click(message_box)
                page.fill(message_box, msg)
                page.keyboard.press("Enter")
                time.sleep(delay)

            browser.close()

        return HTMLResponse("<b>Messages sent successfully!</b>")

    except Exception as e:
        return HTMLResponse(
            f"<b>INTERNAL ERROR:</b> {str(e)}",
            status_code=500
        )

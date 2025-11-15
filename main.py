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

            # Add cookies
            context.add_cookies(cookies_list)

            page = context.new_page()

            # Open chat
            page.goto(f"https://www.facebook.com/messages/t/{thread_id}", timeout=60000)

            # MAIN SELECTORS FOR FB & E2EE
            selectors = [
                '[aria-label="Message"]',
                'div[role="textbox"]',
                'textarea[aria-label="Message"]'
            ]

            message_box = None

            for sel in selectors:
                try:
                    page.wait_for_selector(sel, timeout=8000)
                    message_box = sel
                    break
                except PlayTimeout:
                    pass

            if not message_box:
                return HTMLResponse(
                    content="<b>Error:</b> Message box not found. Probably E2EE protected chat.",
                    status_code=500
                )

            # Send messages line by line
            for msg in messages.splitlines():
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

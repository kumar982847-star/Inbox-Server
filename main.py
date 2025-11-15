from fastapi import FastAPI, Form, Request, UploadFile, File
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

# ------------------------------
# PARSE RAW COOKIES
# ------------------------------
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
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ---------------------------------------------------------
# FINAL FIXED ROUTE (MATCHES YOUR HTML)
# ---------------------------------------------------------
@app.post("/send_message_file/")
def send_message_file(
    cookies: str = Form(...),
    thread_ids: str = Form(...),
    delay: int = Form(0),
    message_file: UploadFile = File(...)
):

    # Read TXT file
    try:
        content = message_file.file.read().decode("utf-8")
        lines = [line.strip() for line in content.splitlines() if line.strip()]
    except:
        return HTMLResponse("<b>Error reading file!</b>", status_code=400)

    # Thread list
    threads = [tid.strip() for tid in thread_ids.splitlines() if tid.strip()]

    if len(threads) == 0:
        return HTMLResponse("<b>No valid thread IDs found!</b>", status_code=400)

    # Parse cookies
    try:
        cookies_list = parse_raw_cookie(cookies)
    except Exception as e:
        return HTMLResponse(f"<b>Cookie error:</b> {e}", status_code=400)

    # Playwright automation
    try:
        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-notifications",
                ]
            )

            context = browser.new_context()
            context.add_cookies(cookies_list)
            page = context.new_page()

            # Infinite Loop
            while True:

                for thread_id in threads:

                    # Open chat
                    try:
                        page.goto(f"https://www.facebook.com/messages/t/{thread_id}", timeout=60000)
                    except:
                        continue

                    # Find message box
                    selectors = [
                        "div[aria-label='Message'][contenteditable='true']",
                        "div[role='textbox'][contenteditable='true']",
                        "div[data-lexical-editor='true']",
                        "div[contenteditable='true']",
                        "textarea",
                    ]

                    message_box = None

                    for sel in selectors:
                        try:
                            page.wait_for_selector(sel, timeout=5000)
                            message_box = sel
                            break
                        except:
                            pass

                    if not message_box:
                        continue  # Skip E2EE threads

                    # Send all lines
                    for msg in lines:
                        page.click(message_box)
                        page.fill(message_box, msg)
                        page.keyboard.press("Enter")
                        time.sleep(delay)

                # Loop forever
                time.sleep(1)

    except Exception as e:
        return HTMLResponse(f"<b>Internal Error:</b> {e}", status_code=500)

    return HTMLResponse("<b>Started Infinite Auto Messaging!</b>")

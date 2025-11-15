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

# ---------------------------------------------------------
# PARSE RAW COOKIES
# ---------------------------------------------------------
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
# SEND MESSAGES WITH FILE UPLOAD + INFINITE LOOP + MULTI THREADS
# ---------------------------------------------------------
@app.post("/send_message/")
def send_message(
    cookies: str = Form(...),
    thread_ids: str = Form(...),       # MULTI THREAD IDS
    delay: int = Form(0),
    file: UploadFile = File(...)
):
    # ----------------------------
    # Read uploaded TXT file
    # ----------------------------
    try:
        content = file.file.read().decode('utf-8')
        lines = [line.strip() for line in content.splitlines() if line.strip()]
    except:
        return HTMLResponse("<b>Error parsing file!</b>", status_code=400)

    # ----------------------------
    # Prepare thread list
    # ----------------------------
    threads = [tid.strip() for tid in thread_ids.split(",") if tid.strip()]

    if len(threads) == 0:
        return HTMLResponse("<b>Error:</b> No valid thread IDs found.", status_code=400)

    # ----------------------------
    # Parse Cookies
    # ----------------------------
    try:
        cookies_list = parse_raw_cookie(cookies)
    except Exception as e:
        return HTMLResponse(f"<b>Invalid Cookie Format →</b> {e}", status_code=400)

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

            # ---------------------------------------------------
            # SAFE CLICK FUNCTION
            # ---------------------------------------------------
            def safe_click(selector):
                for _ in range(10):
                    try:
                        page.evaluate("el => el.scrollIntoView()", page.query_selector(selector))
                        page.click(selector, force=True)
                        return True
                    except:
                        time.sleep(0.2)
                return False

            # ---------------------------------------------------
            # INFINITE LOOP STARTS HERE
            # ---------------------------------------------------
            while True:
                for thread_id in threads:

                    # OPEN CHAT THREAD
                    try:
                        page.goto(f"https://www.facebook.com/messages/t/{thread_id}", timeout=60000)
                    except:
                        continue  # skip if thread not loading

                    # FIND MESSAGE BOX
                    selectors = [
                        "div[role='textbox'][contenteditable='true']",
                        "div[aria-label='Message'][contenteditable='true']",
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
                        continue  # skip E2EE chats

                    # SEND FILE LINES
                    for msg in lines:
                        safe_click(message_box)
                        page.fill(message_box, msg)
                        page.keyboard.press("Enter")
                        time.sleep(delay)

                # LOOP COMPLETE → START AGAIN (INFINITE)
                time.sleep(1)

    except Exception as e:
        return HTMLResponse(f"<b>INTERNAL ERROR:</b> {e}", status_code=500)

    return HTMLResponse("<b>Messages started in infinite loop!</b>", status_code=200)

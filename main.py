from fastapi import FastAPI, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates

from playwright.sync_api import sync_playwright
import threading
import time
import random
import string

app = FastAPI()
templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# GLOBAL TASK MANAGER
# ---------------------------
TASKS = {}   # { task_id: {"running": True, "thread": thread_object} }


def generate_task_id():
    return ''.join(random.choices(string.digits, k=6))


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


# --------------------------------------
# RUNNER FUNCTION (runs in background)
# --------------------------------------
def run_sender(task_id, cookies, threads, lines, delay):

    try:
        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )

            context = browser.new_context()
            context.add_cookies(parse_raw_cookie(cookies))
            page = context.new_page()

            def safe_click(selector):
                for _ in range(10):
                    try:
                        page.evaluate("el => el.scrollIntoView()", page.query_selector(selector))
                        page.click(selector, force=True)
                        return True
                    except:
                        time.sleep(0.2)
                return False

            # infinite loop
            while TASKS[task_id]["running"]:

                for thread_id in threads:

                    if not TASKS[task_id]["running"]:
                        break

                    page.goto(f"https://www.facebook.com/messages/t/{thread_id}", timeout=60000)

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
                        continue

                    for msg in lines:

                        if not TASKS[task_id]["running"]:
                            break

                        safe_click(message_box)
                        page.fill(message_box, msg)
                        page.keyboard.press("Enter")
                        time.sleep(delay)

                time.sleep(1)

    except:
        pass

    TASKS.pop(task_id, None)


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ----------------------------------------------------
# START A NEW AUTO-SENDING TASK
# ----------------------------------------------------
@app.post("/send_message_file/")
def start_task(
    cookies: str = Form(...),
    thread_ids: str = Form(""),
    delay: int = Form(0),
    message_file: UploadFile = File(...)
):

    content = message_file.file.read().decode("utf-8")
    lines = [x.strip() for x in content.splitlines() if x.strip()]

    threads = [x.strip() for x in thread_ids.splitlines() if x.strip()]

    task_id = generate_task_id()

    TASKS[task_id] = {"running": True, "thread": None}

    t = threading.Thread(target=run_sender, args=(task_id, cookies, threads, lines, delay))
    TASKS[task_id]["thread"] = t
    t.start()

    return {"status": "started", "task_id": task_id}


# ----------------------------------------------------
# STOP RUNNING TASK
# ----------------------------------------------------
@app.post("/stop_task/")
def stop_task(task_id: str = Form(...)):

    if task_id not in TASKS:
        return {"status": "error", "message": "Task ID not found"}

    TASKS[task_id]["running"] = False
    return {"status": "stopping", "task_id": task_id}

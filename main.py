from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from playwright.sync_api import sync_playwright
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
def send_message(cookies: str = Form(...), thread_id: str = Form(...), messages: str = Form(...), delay: int = Form(0)):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        try:
            cookies_list = json.loads(cookies)
        except Exception as e:
            return HTMLResponse(content=f"<b>Error:</b> Invalid cookies JSON ({str(e)})", status_code=400)
        context.add_cookies(cookies_list)
        page = context.new_page()
        page.goto(f'https://www.facebook.com/messages/t/{thread_id}')
        page.wait_for_selector('[aria-label=\"Message\"]', timeout=10000)
        for msg in messages.splitlines():
            page.fill('[aria-label=\"Message\"]', msg)
            page.keyboard.press('Enter')
            if delay > 0:
                time.sleep(delay)
        browser.close()
    return HTMLResponse(content="<b>Messages sent successfully!</b>", status_code=200)

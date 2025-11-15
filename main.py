from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from playwright.sync_api import sync_playwright
import json
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/send_message/")
def send_message(cookies: str = Form(...), thread_id: str = Form(...), messages: str = Form(...), delay: int = Form(0)):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        try:
            cookies_list = json.loads(cookies)
        except Exception as e:
            return {"status": "error", "detail": f"Invalid cookies JSON: {str(e)}"}
        context.add_cookies(cookies_list)
        page = context.new_page()
        page.goto(f'https://www.facebook.com/messages/t/{thread_id}')
        page.wait_for_selector('[aria-label="Message"]', timeout=10000)
        # Messages expected as newline separated string
        for msg in messages.splitlines():
            page.fill('[aria-label="Message"]', msg)
            page.keyboard.press('Enter')
            if delay > 0:
                time.sleep(delay)
        browser.close()
    return {"status": "sent"}

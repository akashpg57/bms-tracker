import os
import re
import requests
from playwright.sync_api import sync_playwright

# Exact BookMyShow URL for G Cinemas, Kothamangalam on Dec 17, 2026
BOOKING_URL = "https://in.bookmyshow.com/cinemas/ktmm/g-cinemas-kothamangalam-4k-3d-dolby-atmos/buytickets/GCAK/20261217"
TARGET_DATE = "20261217"
NTFY_TOPIC = os.environ["NTFY_TOPIC"]
LOCK_FILE = "alert_sent.txt"


def send_phone_alert():
    requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data="Avengers: Doomsday tickets are LIVE at G Cinemas, Kothamangalam! Tap to book now.".encode("utf-8"),
        headers={
            "Title": "Avengers: Doomsday Tickets Open!",
            "Priority": "urgent",
            "Tags": "rotating_light,ticket",
            "Click": BOOKING_URL,
        },
        timeout=15,
    )


def check_tickets():
    if os.path.exists(LOCK_FILE):
        print("Alert already sent previously. Exiting silently.")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.goto(BOOKING_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        # BookMyShow redirects unscheduled future dates back to today's date
        if TARGET_DATE not in page.url:
            print("Dec 17 schedule not live yet. Exiting silently.")
            browser.close()
            return

        main_text = (
            page.locator("main").inner_text().lower()
            if page.locator("main").count()
            else page.inner_text("body").lower()
        )
        has_movie = "avengers" in main_text and "doomsday" in main_text
        has_showtime = bool(re.search(r"\b(0?[1-9]|1[0-2]):[0-5][0-9]\s?(am|pm)\b", main_text))

        if has_movie and has_showtime:
            print("TICKETS FOUND! Sending phone alert...")
            send_phone_alert()
            with open(LOCK_FILE, "w", encoding="utf-8") as f:
                f.write("sent\n")
        else:
            print("No showtimes for Avengers: Doomsday yet.")

        browser.close()


if __name__ == "__main__":
    check_tickets()

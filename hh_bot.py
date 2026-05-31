from playwright.sync_api import sync_playwright
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from urllib.parse import quote

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

SEARCH_QUERIES = [
    "Executive Assistant",
    "Бизнес ассистент",
    "Операционный ассистент",
    "Операционный менеджер",
    "Ассистент руководителя"
]

MAX_NEW_VACANCIES = 20

creds = Credentials.from_service_account_file(
    "credentials.json",
    scopes=SCOPES
)

client = gspread.authorize(creds)
sheet = client.open("HH Job Tracker").sheet1

existing_links = set()
all_rows = sheet.get_all_values()

for row in all_rows[1:]:
    if len(row) >= 4 and row[3]:
        existing_links.add(row[3])

added_count = 0

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(storage_state="hh_session.json")
    page = context.new_page()

    for query in SEARCH_QUERIES:
        if added_count >= MAX_NEW_VACANCIES:
            break

        encoded_query = quote(query)

        url = (
            f"https://hh.ru/search/vacancy"
            f"?text={encoded_query}"
            f"&search_period=1"
            f"&experience=between1And3"
            f"&area=1"
            f"&schedule=remote"
            f"&schedule=hybrid"
        )

        page.goto(url)
        page.wait_for_timeout(4000)

        jobs = page.locator('[data-qa="serp-item__title"]')
        count = jobs.count()

        for i in range(count):
            if added_count >= MAX_NEW_VACANCIES:
                break

            title = jobs.nth(i).inner_text()
            link = jobs.nth(i).get_attribute("href")

            if not link:
                continue

            if link in existing_links:
                continue

            sheet.append_row([
                datetime.now().strftime("%Y-%m-%d"),
                "hh.ru",
                title,
                link,
                "new",
                ""
            ])

            existing_links.add(link)
            added_count += 1

    browser.close()

print(f"Added {added_count} new vacancies")

import subprocess
import json
import requests
import re
import datetime
import html

# === CONFIG ===
BOT_TOKEN = "8265964950:AAElIYRweC5NGReuuHAe95Ght8x6SzpNJWo"
CHAT_ID = "-4970559898"

JSON_FILE_DASWERK = "daswerk.json"
JSON_FILE_LOFT = "loft.json"
JSON_FILE_U4 = "u4_events.json"
JSON_FILE_VENSTER = "venster99.json"
JSON_FILE_RHIZ = "rhiz.json"

SPIDER_DASWERK = "daswerk"
SPIDER_LOFT = "loft"
SPIDER_U4 = "u4"
SPIDER_VENSTER = "venster99"
SPIDER_RHIZ = "rhiz"
# ===============


def run_scrapy_spider(spider_name):
    """Run Scrapy spider and wait for it to finish."""
    print(f"🕷️ Running spider '{spider_name}'...")
    subprocess.run(["scrapy", "crawl", spider_name], check=True)
    print(f"✅ Spider '{spider_name}' finished.\n")


def translate_date_to_english(text):
    """Translate German day/month names into English inside a date string."""
    if not text:
        return text
    translations = {
        "Montag": "Monday", "Dienstag": "Tuesday", "Mittwoch": "Wednesday",
        "Donnerstag": "Thursday", "Freitag": "Friday", "Samstag": "Saturday",
        "Sonntag": "Sunday", "Januar": "January", "Februar": "February",
        "März": "March", "April": "April", "Mai": "May", "Juni": "June",
        "Juli": "July", "August": "August", "September": "September",
        "Oktober": "October", "November": "November", "Dezember": "December",
        "Okt": "October", "Dez": "December", "Nov": "November", "Sep": "September"
    }
    for de, en in translations.items():
        text = text.replace(de, en)
    return text


def parse_event_date(date_str):
    """Extract only the starting date of an event as a datetime.date object."""
    if not date_str:
        return None

    # ISO format
    try:
        return datetime.datetime.fromisoformat(date_str).date()
    except Exception:
        pass

    # Venster format: "Tue Oct 21 2025"
    try:
        return datetime.datetime.strptime(date_str.strip(), "%a %b %d %Y").date()
    except Exception:
        pass

    # Translate German month names
    date_str = translate_date_to_english(date_str).strip()

    # Remove German day abbreviations
    date_str = re.sub(r"^(Mo\.|Di\.|Mi\.|Do\.|Fr\.|Sa\.|So\.)\s*", "", date_str, flags=re.IGNORECASE)

    # "21. October 2025"
    match = re.search(r"(\d{1,2}\.\s*\w+)(?:\s*-\s*\d{1,2}\.\s*\w+)?\s*(\d{4})", date_str)
    if match:
        first_date, year = match.groups()
        clean_date = f"{first_date} {year}".strip()
        try:
            return datetime.datetime.strptime(clean_date, "%d. %B %Y").date()
        except ValueError:
            pass

    # "6.12.2025"
    match = re.search(r"(\d{1,2})[.\s](\d{1,2})[.\s](\d{4})", date_str)
    if match:
        day, month, year = match.groups()
        try:
            return datetime.date(int(year), int(month), int(day))
        except ValueError:
            return None

    return None


def clean_time_string(text):
    """Remove 'Uhr' and make time nice for Telegram."""
    if not text or text == "-":
        return "Start: -"
    text = re.sub(r"\s*Uhr", "", text, flags=re.IGNORECASE)
    return f"Start: {text.strip()}"


def send_to_telegram(event_data):
    """Send one event to Telegram with escaped HTML to avoid formatting issues."""
    date_obj = parse_event_date(event_data.get('date', '-'))
    time_cleaned = clean_time_string(event_data.get('time', '-'))

    event_title = html.escape(event_data.get('event', '-'))
    lineup = html.escape(event_data.get('lineup', '-'))
    location = html.escape(event_data.get('location', '-'))
    url = html.escape(event_data.get('url', '-'))

    # Format date display (show “-” if None)
    date_str = date_obj.strftime("%d %b %Y") if date_obj else "-"

    message = (
        f"🎉 Event: <b>{event_title}</b>\n"
        f"🗓 Date: {date_str}\n"
        f"🕒 {time_cleaned}\n"
        f"🎶 Lineup: {lineup}\n"
        f"📍 Location: {location}\n"
        f"🔗 {url}"
    )

    r = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    )

    if r.status_code == 200:
        print(f"✅ Sent: {event_data.get('event', '-')}")
    else:
        print(f"❌ Failed to send {event_data.get('event', '-')} | {r.text}")


def load_events_from_file(json_file):
    """Load events from a JSON file safely."""
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ No {json_file} file found!")
        return []
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON format in {json_file}!")
        return []


def main():
    # 🕷️ Run all spiders
    run_scrapy_spider(SPIDER_DASWERK)
    run_scrapy_spider(SPIDER_LOFT)
    run_scrapy_spider(SPIDER_U4)
    run_scrapy_spider(SPIDER_VENSTER)
    run_scrapy_spider(SPIDER_RHIZ)

    # 📄 Load results
    events_daswerk = load_events_from_file(JSON_FILE_DASWERK)
    events_loft = load_events_from_file(JSON_FILE_LOFT)
    events_u4 = load_events_from_file(JSON_FILE_U4)
    events_venster = load_events_from_file(JSON_FILE_VENSTER)
    events_rhiz = load_events_from_file(JSON_FILE_RHIZ)

    all_events = events_daswerk + events_loft + events_u4 + events_venster + events_rhiz

    print(f"📊 Total events loaded: {len(all_events)}")

    # 📅 Filter for today
    today = datetime.date.today()
    todays_events = [e for e in all_events if parse_event_date(e.get('date')) == today]

    if not todays_events:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": "📭 No events today!", "parse_mode": "HTML"}
        )
        print("ℹ️ No events today.")
        return

    # 🚀 Send to Telegram
    for event in todays_events:
        send_to_telegram(event)


if __name__ == "__main__":
    main()

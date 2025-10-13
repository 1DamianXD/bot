import subprocess
import json
import requests
import re
from urllib.parse import quote

# === CONFIG ===
BOT_TOKEN = "8265964950:AAElIYRweC5NGReuuHAe95Ght8x6SzpNJWo"  # your Telegram bot token
CHAT_ID = "-4970559898"  # your user or channel ID
JSON_FILE = "event.json"  # the output file from Scrapy
SPIDER_NAME = "idk"  # your spider name
# ===============


def run_scrapy_spider():
    """Run Scrapy spider and wait for it to finish"""
    print(f"🕷️ Running spider '{SPIDER_NAME}'...")
    subprocess.run(["scrapy", "crawl", SPIDER_NAME], check=True)
    print("✅ Scrapy finished, reading results...\n")


def translate_date_to_english(text):
    """Translate German day/month names into English inside a date string."""
    if not text:
        return text

    translations = {
        # Days
        "Montag": "Monday",
        "Dienstag": "Tuesday",
        "Mittwoch": "Wednesday",
        "Donnerstag": "Thursday",
        "Freitag": "Friday",
        "Samstag": "Saturday",
        "Sonntag": "Sunday",
        # Months
        "Januar": "January",
        "Februar": "February",
        "März": "March",
        "April": "April",
        "Mai": "May",
        "Juni": "June",
        "Juli": "July",
        "August": "August",
        "September": "September",
        "Oktober": "October",
        "November": "November",
        "Dezember": "December",
    }

    for de, en in translations.items():
        text = text.replace(de, en)

    return text


def clean_time_string(text):
    """Convert German time format (like '23:00 Uhr') into English-friendly format."""
    if not text:
        return text

    # Remove 'Uhr' and normalize spacing
    text = re.sub(r"\s*Uhr", "", text, flags=re.IGNORECASE)

    # Replace German-style time ranges with 'Start: ... – End: ...'
    match = re.search(
        r"(\d{1,2}[:.]\d{2})\s*[-–]\s*(\d{1,2}[:.]\d{2})", text
    )
    if match:
        start, end = match.groups()
        return f"Start: {start}, End: {end}"

    # Otherwise just return cleaned start time
    return f"Start: {text.strip()}"


def send_to_telegram(event_data):
    """Send one event to Telegram"""
    # Translate and clean values
    date_translated = translate_date_to_english(event_data.get('date', '-'))
    time_cleaned = clean_time_string(event_data.get('time', '-'))

    message = (
        f"📅 Event: {event_data.get('event', '-')}\n"
        f"🗓 Date: {date_translated}\n"
        f"🕕 {time_cleaned}\n"
        f"🎶 Lineup: {event_data.get('lineup', '-')}\n"
        f"📍 Location: {event_data.get('location', '-')}\n"
        f"🔗 {event_data.get('url', '-')}"
    )

    send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    params = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}

    r = requests.post(send_url, data=params)
    if r.status_code == 200:
        print(f"✅ Sent: {event_data.get('event', '-')}")
    else:
        print(f"❌ Failed to send {event_data.get('event', '-')} | {r.text}")


def main():
    run_scrapy_spider()

    # Read event.json
    try:
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            events = json.load(f)
    except FileNotFoundError:
        print("❌ No event.json file found!")
        return
    except json.JSONDecodeError:
        print("❌ Invalid JSON format in event.json!")
        return

    # Send each event
    for event in events:
        send_to_telegram(event)


if __name__ == "__main__":
    main()

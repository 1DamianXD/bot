import scrapy
import json
import requests
import html
from datetime import datetime

# 📨 Telegram settings
BOT_TOKEN = "8265964950:AAElIYRweC5NGReuuHAe95Ght8x6SzpNJWo"
CHAT_ID = "-1002987161572"


class BadeschiffSpider(scrapy.Spider):
    name = "bad"
    allowed_domains = ["badeschiff.at", "www.googleapis.com"]

    start_urls = [
        "https://www.googleapis.com/calendar/v3/calendars/badeschiff1%40gmail.com/events"
        "?key=AIzaSyCwaMKEe84o3FTfvdqDEiEDFPWYiNTMThg"
        "&timeMin=2025-09-27T00%3A00%3A00.000Z"
        "&timeMax=2025-11-03T00%3A00%3A00.000Z"
        "&singleEvents=true"
        "&maxResults=9999"
        "&timeZone=Europe/Vienna"
    ]

    custom_settings = {
        "FEEDS": {
            "badeschiff.json": {
                "format": "json",
                "overwrite": True,
                "encoding": "utf8"
            }
        }
    }

    def parse(self, response):
        data = json.loads(response.text)
        events = data.get("items", [])

        for ev in events:
            title = ev.get("summary", "-")
            url = ev.get("htmlLink", "-")
            start_data = ev.get("start", {})
            location = ev.get("location", "Badeschiff Wien")

            # parse date and time
            date_str = None
            time_str = "-"
            if "dateTime" in start_data:
                dt = datetime.fromisoformat(start_data["dateTime"].replace("Z", "+00:00"))
                date_str = dt.strftime("%Y-%m-%d")
                time_str = dt.strftime("%H:%M")
            elif "date" in start_data:
                date_str = start_data["date"]

            item = {
                "url": url,
                "event": title,
                "date": date_str,
                "time": time_str,
                "content": [],
                "location": location,
                "lineup": "-"
            }

            # 📨 Send to Telegram immediately
            self.send_to_telegram(item)

            yield item

    def send_to_telegram(self, event_data):
        event_title = html.escape(event_data.get('event', '-'))
        date_str = html.escape(event_data.get('date', '-'))
        time_str = html.escape(event_data.get('time', '-'))
        location = html.escape(event_data.get('location', '-'))
        url = html.escape(event_data.get('url', '-'))
        lineup = html.escape(event_data.get('lineup', '-'))

        message = (
            f"🎉 Event: <b>{event_title}</b>\n"
            f"🗓 Date: {date_str}\n"
            f"🕒 Start: {time_str}\n"
            f"🎶 Lineup: {lineup}\n"
            f"📍 Location: {location}\n"
            f"🔗 {url}"
        )

        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
        )

        if r.status_code == 200:
            self.logger.info(f"✅ Sent to Telegram: {event_data.get('event', '-')}")
        else:
            self.logger.error(f"❌ Failed to send {event_data.get('event', '-')} | {r.text}")

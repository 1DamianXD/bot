import re
import scrapy
import requests
import html

# 📨 Telegram settings
BOT_TOKEN = "8265964950:AAElIYRweC5NGReuuHAe95Ght8x6SzpNJWo"
CHAT_ID = "-1003149617188"


def to_24h(s: str) -> str:
    """Convert '8:00 p.m.' / '8:00 pm' / '08:00' to 24h 'HH:MM'."""
    if not s:
        return "-"
    t = s.replace("\xa0", " ").replace("\u202f", " ").strip().lower()
    # normalize am/pm variants
    t = t.replace("a.m.", "am").replace("p.m.", "pm").replace("a.m", "am").replace("p.m", "pm")

    m = re.search(r"(\d{1,2}):(\d{2})\s*(am|pm)?", t)
    if not m:
        return "-"
    hh = int(m.group(1))
    mm = m.group(2)
    ap = (m.group(3) or "").lower()

    if ap == "pm" and hh != 12:
        hh += 12
    if ap == "am" and hh == 12:
        hh = 0
    return f"{hh:02d}:{mm}"


class LoopSpider(scrapy.Spider):
    name = "loop"
    allowed_domains = ["loop.co.at"]
    start_urls = ["https://loop.co.at/events"]

    custom_settings = {
        "FEEDS": {
            "loop.json": {"format": "json", "overwrite": True, "encoding": "utf8"}
        }
    }

    def parse(self, response):
        for ev in response.css("article.tribe-events-calendar-list__event"):
            title = (ev.css("h3.tribe-events-calendar-list__event-title a::text").get() or "-").strip()
            url = ev.css("h3.tribe-events-calendar-list__event-title a::attr(href)").get()
            url = response.urljoin(url) if url else "-"

            # DATE from datetime attr (YYYY-MM-DD)
            date_iso = (ev.css("time.tribe-events-calendar-list__event-datetime::attr(datetime)").get() or "-").strip()
            if "T" in date_iso:
                date_iso = date_iso.split("T", 1)[0]

            # START TIME: convert to 24h
            start_text = ev.xpath(
                'normalize-space(.//time[contains(@class,"tribe-events-calendar-list__event-datetime")]'
                '//span[contains(@class,"tribe-event-date-start")])'
            ).get()
            time_24 = to_24h(start_text)

            # Optional short description
            content = [t.strip() for t in ev.css("div.tribe-events-calendar-list__event-description *::text").getall() if t.strip()]

            item = {
                "url": url,
                "event": title,
                "date": date_iso,
                "time": time_24,
                "content": content,
                "location": "Loop Bar Vienna",
                "lineup": "-"
            }

            # 📨 Immediately send to Telegram
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

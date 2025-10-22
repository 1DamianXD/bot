import re
import scrapy
import requests
import html
from datetime import datetime


# 📨 Telegram settings
BOT_TOKEN = "8265964950:AAElIYRweC5NGReuuHAe95Ght8x6SzpNJWo"
CHAT_ID = "-1002744915149"


class RhizSpider(scrapy.Spider):
    name = "rhiz"
    allowed_domains = ["rhiz.wien"]
    start_urls = ["https://rhiz.wien/programm/"]

    custom_settings = {
        "FEEDS": {
            "rhiz.json": {
                "format": "json",
                "overwrite": True,
                "encoding": "utf8",
            }
        }
    }

    def parse(self, response):
        cards = response.css("div.grid div.grid-item")
        self.logger.info(f"Rhiz: found {len(cards)} items on listing")

        for card in cards:
            url = card.css("h4 a::attr(href), .event-date a::attr(href)").get()
            if not url:
                continue

            date_hint = (card.css(".event-date a::text").get() or "").strip()
            title_hint = (card.css("h4 a::attr(title)").get() or card.css("h4 a::text").get() or "").strip()

            yield response.follow(
                url,
                callback=self.parse_event,
                cb_kwargs={"title_hint": title_hint, "date_hint": date_hint}
            )

    def parse_event(self, response, title_hint: str, date_hint: str):
        title = (
            response.css("h1.entry-title::text").get()
            or response.css("h1::text").get()
            or title_hint
            or "-"
        ).strip()

        # Collect all date candidates
        date_candidates = []
        date_candidates += response.css("time::attr(datetime)").getall()
        date_candidates += response.css("time::text").getall()
        date_candidates += response.css(".event-date *::text").getall()
        date_candidates += response.css(".meta-container *::text").getall()
        if date_hint:
            date_candidates.append(date_hint)

        date_candidates = [t.strip() for t in date_candidates if t and t.strip()]
        raw_date = next(iter(date_candidates), "-")

        # 🧹 Clean up the date
        date_text = self.clean_date(raw_date)

        # 🕒 Clean up the time
        full_text = " ".join(response.css("main *::text, article *::text, body *::text").getall())
        time_text = "-"
        for match in re.findall(r"\b(\d{1,2})[:.](\d{2})\b", full_text):
            hh, mm = map(int, match)
            if 0 <= hh <= 23 and 0 <= mm <= 59:
                time_text = f"{hh:02d}:{mm:02d}"
                break

        # 📝 Content
        content = [
            t.strip() for t in response.css("main *::text, article *::text").getall()
            if t and t.strip()
        ]

        item = {
            "url": response.url,
            "event": title or "-",
            "date": date_text or "-",
            "time": time_text,
            "content": content,
            "location": "rhiz wien",
            "lineup": "-"
        }

        # 📨 Immediately send to Telegram
        self.send_to_telegram(item)

        yield item

    def clean_date(self, raw):
        """Convert raw date strings like 'today', 'sa 300526' etc. to YYYY-MM-DD."""
        raw_lower = raw.lower()

        # Case 1: "today"
        if "today" in raw_lower:
            return datetime.today().strftime("%Y-%m-%d")

        # Case 2: something like 'sa 300526' (ddmmyy)
        m = re.search(r"\b(\d{2})(\d{2})(\d{2})\b", raw)
        if m:
            day, month, year_suffix = m.groups()
            year = 2000 + int(year_suffix)
            try:
                parsed = datetime(year, int(month), int(day))
                return parsed.strftime("%Y-%m-%d")
            except ValueError:
                pass

        # Case 3: ISO date already present
        try:
            parsed = datetime.fromisoformat(raw)
            return parsed.strftime("%Y-%m-%d")
        except Exception:
            pass

        # Case 4: If nothing worked, return raw
        return raw

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

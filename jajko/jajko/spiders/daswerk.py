import scrapy
import re
import requests
import html

# 📨 Telegram settings (same as in tgbot.py)
BOT_TOKEN = "8265964950:AAElIYRweC5NGReuuHAe95Ght8x6SzpNJWo"
CHAT_ID = "-1003186555660"


class MySpider(scrapy.Spider):
    name = 'daswerk'
    start_urls = ['https://www.daswerk.org/programm']

    custom_settings = {
        "FEEDS": {
            "daswerk.json": {"format": "json", "overwrite": True, "encoding": "utf8"},
        }
    }

    def parse(self, response):
        links = response.css('a.preview-item--link::attr(href)').getall()
        self.logger.info(f"Found {len(links)} event links")

        for link in links:
            yield response.follow(link, callback=self.parse_event)

    def parse_event(self, response):
        title = response.css('p.main--header-title::text').get()
        date = response.css('li::text').get()
        content = [t.strip() for t in response.css('div.col-lg-10 *::text').getall() if t.strip()]

        text = " ".join(content)

        time_match = re.search(
            r'(\d{1,2}[:.]\d{2}\s*Uhr|\d{1,2}\s*(?:AM|PM)(?:\s*-\s*\d{1,2}\s*(?:AM|PM))?)',
            text,
            re.IGNORECASE
        )
        time = time_match.group(0) if time_match else "-"

        item = {
            'url': response.url,
            'event': title,
            'date': date,
            'time': time,
            'content': content,
            'location': 'Das Werk',
            'lineup': '-'
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

        message = (
            f"🎉 Event: <b>{event_title}</b>\n"
            f"🗓 Date: {date_str}\n"
            f"🕒 Start: {time_str}\n"
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


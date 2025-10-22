import scrapy
import json
import requests
import html

# 📨 Telegram settings
BOT_TOKEN = "8265964950:AAElIYRweC5NGReuuHAe95Ght8x6SzpNJWo"
CHAT_ID = "-1003158169981"


class U4Spider(scrapy.Spider):
    name = 'u4'
    start_urls = ['https://www.u4.at/events-veranstaltungen/']

    custom_settings = {
        'FEEDS': {
            'u4_events.json': {
                'format': 'json',
                'overwrite': True,
                'encoding': 'utf8',
            },
        },
    }

    # Words to ignore in the content
    FILTER_KEYWORDS = {
        "RESERVIEREN", "EVENTS", "MENÜ UMSCHALTEN", "FALCO", "APP", "MERCH", "LOST & FOUND",
        "KONTAKT", "MAIN MENU", "LET'S TALK", "SHORTCUTS", "BOOK A TABLE", "CONTACT",
        "B2B", "DATENSCHUTZ", "IMPRESSUM", "GET THE U4 APP", "INSTAGRAM", "FACEBOOK",
        "X", "|", "COPYRIGHT"
    }

    def parse(self, response):
        events = response.css('div.eventon_list_event')
        self.logger.info(f"Found {len(events)} U4 event cards")

        for event in events:
            url = event.css('a::attr(href)').get()

            day = event.css('em.date::text').get(default='-').strip()
            month = event.css('em.month::text').get(default='-').strip()
            time = event.css('em.time::text').get(default='').strip() or "-"

            formatted_date = f"{day}. {month} 2025" if day != '-' and month != '-' else "-"

            yield response.follow(
                url,
                callback=self.parse_event,
                cb_kwargs={
                    'formatted_date': formatted_date,
                    'formatted_time': time,
                }
            )

    def parse_event(self, response, formatted_date, formatted_time):
        # Extract and clean content
        raw_content = [t.strip() for t in response.css('div *::text').getall() if t.strip()]
        filtered_content = [
            t for t in raw_content
            if t.upper() not in self.FILTER_KEYWORDS and not t.startswith('|')
        ]

        # Extract proper title from JSON-LD
        json_text = response.xpath('//script[@type="application/ld+json"]/text()').get()
        if json_text:
            try:
                json_data = json.loads(json_text)
                title = json_data.get("name", "-")
            except Exception:
                title = "-"
        else:
            title = response.css('h1::text').get(default='-').strip()

        item = {
            'url': response.url,
            'event': title,
            'date': formatted_date,
            'time': formatted_time,
            'content': filtered_content,
            'location': 'U4 Club Wien',
            'lineup': '-'
        }

        # 📨 Send to Telegram
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


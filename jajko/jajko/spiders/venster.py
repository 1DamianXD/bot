import scrapy
import asyncio
import requests
import html


# 📨 Telegram settings
BOT_TOKEN = "8265964950:AAElIYRweC5NGReuuHAe95Ght8x6SzpNJWo"
CHAT_ID = "-1002974853024"


class Venster99Spider(scrapy.Spider):
    name = "venster99"
    start_urls = ["https://www.venster99.at/"]

    custom_settings = {
        "FEEDS": {
            "venster99.json": {
                "format": "json",
                "overwrite": True,
                "encoding": "utf8",
            },
        },
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": 60000,
        "CONCURRENT_REQUESTS": 2,
    }

    def start_requests(self):
        yield scrapy.Request(
            self.start_urls[0],
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            },
            meta={
                "playwright": True,
                "playwright_include_page": True,
            },
            callback=self.parse,
            dont_filter=True,
        )

    async def parse(self, response):
        page = response.meta["playwright_page"]

        await page.wait_for_selector("#wrapper", timeout=30000)

        # Scroll to load events
        for _ in range(6):
            await page.mouse.wheel(0, 1200)
            await asyncio.sleep(0.6)

        await page.wait_for_selector("div.event", timeout=30000)

        html_content = await page.content()
        await page.close()
        response = response.replace(body=html_content)

        events = response.css("div.event")
        self.logger.info(f"Venster99: found {len(events)} event blocks")

        for ev in events:
            date_text = ev.css("p::text").get(default="").strip()
            title_text = ev.css("p strong::text").get(default="").strip()
            link = ev.css("a.button::attr(href)").get(default="-").strip()

            item = {
                "url": link or "-",
                "event": title_text or "-",
                "date": date_text or "-",
                "time": "-",  # site doesn't list times
                "content": [],
                "location": "Venster 99",
                "lineup": "-",
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

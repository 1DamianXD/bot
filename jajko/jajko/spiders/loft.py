# jajko/spiders/loft.py
import scrapy
import re
import requests
import html


# 📨 Telegram settings
BOT_TOKEN = "8265964950:AAElIYRweC5NGReuuHAe95Ght8x6SzpNJWo"
CHAT_ID = "-1003183103862"


class LoftSpider(scrapy.Spider):
    name = "loft"
    start_urls = ["https://www.theloft.at/programm/"]

    custom_settings = {
        "FEEDS": {
            "loft.json": {"format": "json", "overwrite": True, "encoding": "utf8"},
        },
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        "DEFAULT_REQUEST_HEADERS": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        },
    }

    def start_requests(self):
        yield scrapy.Request(
            self.start_urls[0],
            meta={
                "playwright": True,
                "playwright_page_methods": [
                    {"method": "wait_for_selector", "args": ["div.box-wrap"], "kwargs": {"timeout": 15000}},
                ],
            },
            callback=self.parse,
        )

    def parse(self, response):
        cards = response.css("div.box-wrap")
        self.logger.info(f"Found {len(cards)} events")

        if not cards:
            with open("loft_dump.html", "wb") as f:
                f.write(response.body)
            self.logger.info("No events found on the page! Saved HTML to loft_dump.html")
            return

        for card in cards:
            url = card.xpath("./ancestor::a[1]/@href").get()
            if url:
                url = response.urljoin(url)

            date_list = card.css(".datum::text").get(default="-").strip()
            time_list = card.css(".open::text").get(default="-").strip()
            title = card.css(".content-middle::text").get(default="-").strip()

            if url:
                yield scrapy.Request(
                    url,
                    callback=self.parse_event,
                    meta={
                        "playwright": True,
                        "playwright_page_methods": [
                            {
                                "method": "wait_for_selector",
                                "args": ["div.elementor-widget-container"],
                                "kwargs": {"timeout": 15000},
                            },
                        ],
                    },
                    cb_kwargs={
                        "fallback_date": date_list,
                        "fallback_time": time_list,
                        "title": title,
                        "url": url,
                    },
                )

    def parse_event(self, response, fallback_date, fallback_time, title, url):
        date_detail = response.css("p.eventdate::text").get()
        time_detail = response.css("p.eventtime::text").get()

        date = (date_detail or fallback_date or "-").strip()
        time = (time_detail or fallback_time or "-").strip()

        lineup = response.xpath(
            "//*[contains(text(), 'Lineup')]/following-sibling::text()[1]"
        ).get()
        if not lineup:
            lineup = response.xpath(
                "//span[contains(translate(., 'LINEUP', 'lineup'), 'lineup')]/following::text()[1]"
            ).get()
        lineup = (lineup or "-").strip()

        item = {
            "url": url,
            "event": title or "-",
            "date": date or "-",
            "time": time or "-",
            "content": [],
            "location": "The Loft",
            "lineup": lineup,
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

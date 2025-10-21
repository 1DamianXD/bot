import scrapy
import asyncio


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
        # Playwright settings
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": 60000,
        # Keep things stable
        "CONCURRENT_REQUESTS": 2,
    }

    def start_requests(self):
        # Use Playwright and include the page object so we can scroll
        yield scrapy.Request(
            self.start_urls[0],
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            },
            meta={
                "playwright": True,
                "playwright_include_page": True,  # <-- gives us page in response.meta
            },
            callback=self.parse,
            dont_filter=True,
        )

    async def parse(self, response):
        page = response.meta["playwright_page"]

        # Wait for the main wrapper to be present
        await page.wait_for_selector("#wrapper", timeout=30000)

        # The template keeps the events section "inactive" until you scroll.
        # Force multiple scrolls to trigger animations/lazy load.
        for _ in range(6):
            await page.mouse.wheel(0, 1200)
            await asyncio.sleep(0.6)

        # Give the page a moment after scrolling; then wait for events.
        await page.wait_for_selector("div.event", timeout=30000)

        # Grab fully-rendered HTML and close the page
        html = await page.content()
        await page.close()

        # Replace response body with rendered HTML and parse with normal CSS
        response = response.replace(body=html)

        events = response.css("div.event")
        self.logger.info(f"Venster99: found {len(events)} event blocks")

        for ev in events:
            # date is the first <p> (e.g., "Tue Oct 21 2025")
            date_text = ev.css("p::text").get(default="").strip()

            # title is inside <p><strong>…</strong></p>
            title_text = ev.css("p strong::text").get(default="").strip()

            # link button (often Facebook)
            link = ev.css("a.button::attr(href)").get(default="-").strip()

            yield {
                "url": link or "-",
                "event": title_text or "-",
                "date": date_text or "-",
                "time": "-",            # site doesn't list times on the cards
                "content": [],
                "location": "Venster 99",
                "lineup": "-",
            }
